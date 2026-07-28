#!/usr/bin/env python3

import glob
import json
import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from ament_index_python.packages import get_package_share_directory


PACKAGE_SHARE = Path(
    get_package_share_directory("multi_lidar_bringup")
)

CONFIG_DIR = PACKAGE_SHARE / "config"
RESULT_FILE = Path("/tmp/multi_lidar_ports.json")
PROBE_TIMEOUT = 8

SENSOR_PROFILES = [
    {
        "name": "TG30",
        "config": CONFIG_DIR / "tg30.yaml",
        "patterns": [
            r"Model:\s*TG30",
            r"Current Lidar Model Code\s+101",
        ],
    },
    {
        "name": "GS2",
        "config": CONFIG_DIR / "gs2.yaml",
        "patterns": [
            r"Model:\s*GS2",
            r"Current Lidar Model Code\s+51",
        ],
    },
]


def make_probe_config(source: Path, port: str) -> str:
    text = source.read_text(encoding="utf-8")

    updated, count = re.subn(
        r"^(\s*)port:\s*.*$",
        rf"\1port: {port}",
        text,
        count=1,
        flags=re.MULTILINE,
    )

    if count != 1:
        raise RuntimeError(
            f"{source}에서 port 파라미터를 찾지 못했습니다."
        )

    temporary = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        prefix="multi_lidar_probe_",
        delete=False,
        encoding="utf-8",
    )

    temporary.write(updated)
    temporary.close()

    return temporary.name


def stop_process(process: subprocess.Popen) -> str:
    try:
        os.killpg(process.pid, signal.SIGINT)
    except ProcessLookupError:
        pass

    try:
        output, _ = process.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

        output, _ = process.communicate()

    return output or ""


def probe_sensor(port: str, profile: dict) -> tuple[bool, str]:
    temporary_config = make_probe_config(
        profile["config"],
        port,
    )

    safe_port = Path(port).name.replace("-", "_")
    namespace = (
        f"/probe_{profile['name'].lower()}_{safe_port}"
    )

    command = [
        "ros2",
        "run",
        "ydlidar_ros2_driver",
        "ydlidar_ros2_driver_node",
        "--ros-args",
        "--params-file",
        temporary_config,
        "-r",
        f"__ns:={namespace}",
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    try:
        output, _ = process.communicate(
            timeout=PROBE_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        output = stop_process(process)
    finally:
        try:
            os.unlink(temporary_config)
        except FileNotFoundError:
            pass

    time.sleep(0.4)

    detected = any(
        re.search(pattern, output or "", re.IGNORECASE)
        for pattern in profile["patterns"]
    )

    return detected, output or ""


def print_failure_log(output: str) -> None:
    useful_lines = [
        line
        for line in output.splitlines()
        if any(
            word in line
            for word in (
                "Model",
                "Code",
                "connected",
                "failed",
                "Failed",
                "error",
                "Error",
            )
        )
    ]

    for line in useful_lines[-5:]:
        print(f"      {line}", flush=True)


def discover_devices() -> dict[str, str]:
    ports = sorted(glob.glob("/dev/ttyUSB*"))

    if not ports:
        raise RuntimeError(
            "/dev/ttyUSB* 장치를 찾지 못했습니다."
        )

    print("===== YDLidar 자동 탐색 시작 =====", flush=True)
    print(
        f"발견된 포트: {', '.join(ports)}",
        flush=True,
    )

    detected_devices: dict[str, str] = {}

    for port in ports:
        print(f"\n[검사] {port}", flush=True)

        for profile in SENSOR_PROFILES:
            print(
                f"  - {profile['name']} 설정으로 통신 시험 중...",
                flush=True,
            )

            detected, output = probe_sensor(
                port,
                profile,
            )

            if detected:
                detected_devices[port] = profile["name"]
                print(
                    f"    ✅ {port} = {profile['name']}",
                    flush=True,
                )
                break

            print(
                f"    ❌ {profile['name']} 아님",
                flush=True,
            )
            print_failure_log(output)

        else:
            detected_devices[port] = "UNKNOWN"
            print(
                f"    ⚠️ {port} 모델 판별 실패",
                flush=True,
            )

    tg30_ports = sorted(
        port
        for port, model in detected_devices.items()
        if model == "TG30"
    )

    gs2_ports = sorted(
        port
        for port, model in detected_devices.items()
        if model == "GS2"
    )

    unknown_ports = sorted(
        port
        for port, model in detected_devices.items()
        if model == "UNKNOWN"
    )

    result: dict[str, str] = {}

    if tg30_ports:
        result["tg30"] = tg30_ports[0]

    for index, port in enumerate(gs2_ports, start=1):
        result[f"gs2_{index}"] = port

    print("\n===== 자동 탐색 결과 =====", flush=True)

    for name, port in result.items():
        print(f"{name:8s} -> {port}", flush=True)

    if unknown_ports:
        print(
            f"unknown  -> {', '.join(unknown_ports)}",
            flush=True,
        )

    RESULT_FILE.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"\n결과 저장: {RESULT_FILE}",
        flush=True,
    )

    return result


def main() -> int:
    try:
        result = discover_devices()
    except Exception as error:
        print(f"❌ 자동 탐색 오류: {error}", flush=True)
        return 1

    tg30_count = int("tg30" in result)
    gs2_count = sum(
        name.startswith("gs2_")
        for name in result
    )

    if tg30_count == 1 and gs2_count >= 2:
        print(
            "✅ TG30 1대와 GS2 2대 이상을 판별했습니다.",
            flush=True,
        )
        return 0

    print(
        "❌ 필요한 센서 구성을 판별하지 못했습니다.",
        flush=True,
    )
    print(
        f"TG30: {tg30_count}대, GS2: {gs2_count}대",
        flush=True,
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
