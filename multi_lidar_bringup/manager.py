#!/usr/bin/env python3

import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

from ament_index_python.packages import get_package_share_directory

from multi_lidar_bringup.device_discovery import discover_devices


PACKAGE_SHARE = Path(
    get_package_share_directory("multi_lidar_bringup")
)

CONFIG_DIR = PACKAGE_SHARE / "config"
GS2_CONFIG = CONFIG_DIR / "gs2.yaml"
TG30_CONFIG = CONFIG_DIR / "tg30.yaml"

RUNTIME_DIR = Path("/tmp/multi_lidar_runtime")

children: list[tuple[str, subprocess.Popen]] = []
stop_requested = False


def request_stop(signum, frame) -> None:
    global stop_requested
    stop_requested = True


def create_runtime_config(
    source: Path,
    destination: Path,
    port: str,
    frame_id: str,
) -> None:
    text = source.read_text(encoding="utf-8")

    text, port_count = re.subn(
        r"^(\s*)port:\s*.*$",
        rf"\1port: {port}",
        text,
        count=1,
        flags=re.MULTILINE,
    )

    text, frame_count = re.subn(
        r"^(\s*)frame_id:\s*.*$",
        rf"\1frame_id: {frame_id}",
        text,
        count=1,
        flags=re.MULTILINE,
    )

    if port_count != 1:
        raise RuntimeError(
            f"{source}에서 port 파라미터를 찾지 못했습니다."
        )

    if frame_count != 1:
        raise RuntimeError(
            f"{source}에서 frame_id 파라미터를 찾지 못했습니다."
        )

    destination.write_text(
        text,
        encoding="utf-8",
    )


def launch_driver(
    sensor_name: str,
    namespace: str,
    config_path: Path,
) -> None:
    command = [
        "ros2",
        "run",
        "ydlidar_ros2_driver",
        "ydlidar_ros2_driver_node",
        "--ros-args",
        "--params-file",
        str(config_path),
        "-r",
        f"__ns:=/{namespace}",
    ]

    print(f"\n[실행] {sensor_name}", flush=True)
    print(
        f"  namespace: /{namespace}",
        flush=True,
    )
    print(
        f"  config:    {config_path}",
        flush=True,
    )

    process = subprocess.Popen(
        command,
        start_new_session=True,
    )

    children.append(
        (sensor_name, process)
    )


def stop_children() -> None:
    print(
        "\n===== LiDAR 드라이버 종료 중 =====",
        flush=True,
    )

    for name, process in children:
        if process.poll() is not None:
            continue

        print(
            f"[종료 요청] {name}",
            flush=True,
        )

        try:
            os.killpg(
                process.pid,
                signal.SIGINT,
            )
        except ProcessLookupError:
            pass

    deadline = time.time() + 6

    for _, process in children:
        remaining = max(
            0.1,
            deadline - time.time(),
        )

        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(
                    process.pid,
                    signal.SIGKILL,
                )
            except ProcessLookupError:
                pass

    print(
        "LiDAR 드라이버가 모두 종료되었습니다.",
        flush=True,
    )


def main() -> int:
    global stop_requested

    signal.signal(
        signal.SIGINT,
        request_stop,
    )
    signal.signal(
        signal.SIGTERM,
        request_stop,
    )

    if shutil.which("ros2") is None:
        print(
            "❌ ROS2 환경이 로드되지 않았습니다.",
            flush=True,
        )
        return 1

    try:
        mapping = discover_devices()
    except Exception as error:
        print(
            f"❌ 센서 자동 탐색 실패: {error}",
            flush=True,
        )
        return 2

    tg30_port = mapping.get("tg30")

    gs2_items = sorted(
        (
            (name, port)
            for name, port in mapping.items()
            if name.startswith("gs2_")
        ),
        key=lambda item: int(
            item[0].split("_")[1]
        ),
    )

    if not tg30_port and not gs2_items:
        print(
            "❌ 실행할 LiDAR를 찾지 못했습니다.",
            flush=True,
        )
        return 2

    if RUNTIME_DIR.exists():
        shutil.rmtree(RUNTIME_DIR)

    RUNTIME_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\n===== 자동 실행 포트 배정 =====",
        flush=True,
    )
    if tg30_port:
        print(
            f"tg30     -> {tg30_port}",
            flush=True,
        )
    else:
        print(
            "tg30     -> 연결되지 않음 (건너뜀)",
            flush=True,
        )

    for name, port in gs2_items:
        print(
            f"{name:8s} -> {port}",
            flush=True,
        )

    if not gs2_items:
        print(
            "GS2      -> 연결되지 않음 (건너뜀)",
            flush=True,
        )

    if tg30_port:
        tg30_runtime = RUNTIME_DIR / "tg30.yaml"

        create_runtime_config(
            source=TG30_CONFIG,
            destination=tg30_runtime,
            port=tg30_port,
            frame_id="tg30_frame",
        )

        launch_driver(
            sensor_name="TG30",
            namespace="tg30",
            config_path=tg30_runtime,
        )

        time.sleep(1)

    for name, port in gs2_items:
        runtime_config = (
            RUNTIME_DIR / f"{name}.yaml"
        )

        create_runtime_config(
            source=GS2_CONFIG,
            destination=runtime_config,
            port=port,
            frame_id=f"{name}_frame",
        )

        launch_driver(
            sensor_name=name.upper(),
            namespace=name,
            config_path=runtime_config,
        )

        time.sleep(1)

    print(
        "\n✅ 모든 LiDAR 드라이버를 자동 실행했습니다.",
        flush=True,
    )

    exit_code = 0

    try:
        while not stop_requested:
            for name, process in children:
                return_code = process.poll()

                if return_code is not None:
                    print(
                        f"\n❌ {name} 종료, 코드: {return_code}",
                        flush=True,
                    )
                    stop_requested = True
                    exit_code = 1
                    break

            time.sleep(1)

    finally:
        stop_children()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
