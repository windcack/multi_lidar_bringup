# multi_lidar_bringup

YDLidar 센서를 USB 포트에서 자동으로 탐색하고, 발견된 센서만 ROS 2 드라이버로 실행하는 패키지입니다.

YDLidar에서 제공하는 YDLidar-SDK와 ydlidar_ros2_driver를 기반으로 동작하며, Raspberry Pi 부팅 시 systemd를 통해 자동 실행할 수 있습니다.

## 주요 기능

- `/dev/ttyUSB*` 포트 자동 탐색
- GS2 및 TG30 센서 자동 판별
- USB 연결 순서와 관계없이 실행
- 발견된 센서만 선택적으로 실행
- 여러 대의 GS2 동시 지원
- 센서별 ROS 2 namespace 분리
- Foxglove Bridge 자동 실행
- systemd 기반 부팅 자동 실행
- 실행 실패 시 서비스 자동 재시작

## 테스트 환경

- Raspberry Pi 5
- Ubuntu Server 24.04 LTS
- ROS 2 Jazzy Jalisco
- YDLidar-SDK 1.2.20
- ydlidar_ros2_driver 1.0.1
- YDLidar GS2 x2
- YDLidar TG30 x1
- Foxglove Bridge

## 의존성

이 저장소에는 YDLidar-SDK와 ydlidar_ros2_driver가 포함되어 있지 않습니다.

필요한 구성:

- ROS 2 Jazzy
- YDLidar-SDK
- ydlidar_ros2_driver
- foxglove_bridge
- tf2_ros

## 설치

### 1. 필수 패키지 설치

    sudo apt update
    sudo apt install -y git cmake build-essential \
      python3-colcon-common-extensions \
      python3-rosdep \
      ros-jazzy-foxglove-bridge \
      ros-jazzy-tf2-ros

### 2. YDLidar-SDK 설치

    cd ~
    git clone https://github.com/YDLIDAR/YDLidar-SDK.git
    cd YDLidar-SDK
    mkdir -p build
    cd build
    cmake ..
    cmake --build . -j$(nproc)
    sudo cmake --install .
    sudo ldconfig

### 3. ROS 2 워크스페이스 생성

    mkdir -p ~/ydlidar_ros2_ws/src
    cd ~/ydlidar_ros2_ws/src

### 4. YDLidar ROS 2 드라이버 설치

    git clone https://github.com/YDLIDAR/ydlidar_ros2_driver.git

### 5. multi_lidar_bringup 설치

    git clone https://github.com/windcack/multi_lidar_bringup.git

### 6. 빌드

    cd ~/ydlidar_ros2_ws
    source /opt/ros/jazzy/setup.bash
    rosdep install --from-paths src --ignore-src -r -y
    colcon build --symlink-install
    source install/setup.bash

## 수동 실행

    source /opt/ros/jazzy/setup.bash
    source ~/ydlidar_ros2_ws/install/setup.bash
    ros2 launch multi_lidar_bringup multi_lidar.launch.py

## 실행되는 토픽

GS2:

- `/gs2_1/scan`
- `/gs2_1/point_cloud`
- `/gs2_2/scan`
- `/gs2_2/point_cloud`
- 추가 GS2는 `/gs2_3`, `/gs2_4` 순서로 생성

TG30:

- `/tg30/scan`
- `/tg30/point_cloud`

## Foxglove 연결

Launch 실행 시 Foxglove Bridge가 8765 포트에서 실행됩니다.

연결 주소:

    ws://라즈베리파이_IP:8765

Foxglove 3D 패널 설정:

- Fixed frame: `base_link`
- Display frame: `base_link`

## 부팅 자동 실행 설치

먼저 워크스페이스 빌드를 완료해야 합니다.

    cd ~/ydlidar_ros2_ws/src/multi_lidar_bringup
    sudo bash scripts/install_service.sh

서비스 상태 확인:

    systemctl status multi-lidar.service --no-pager -l

서비스 로그 확인:

    journalctl -u multi-lidar.service -f

서비스 재시작:

    sudo systemctl restart multi-lidar.service

## 자동 탐색 과정의 오류 로그

센서 자동 탐색 중 잘못된 모델 설정으로 시험하면서 다음 로그가 일시적으로 표시될 수 있습니다.

- `Error, cannot retrieve Lidar health code`
- `Fail to get baseplate device information`
- `Failed to start the lidar`

이후 센서 모델이 정상적으로 판별되고 최종 드라이버가 실행된다면 정상 동작입니다.

## 패키지 구조

    multi_lidar_bringup/
    ├── config/
    ├── launch/
    ├── multi_lidar_bringup/
    │   ├── device_discovery.py
    │   └── manager.py
    ├── resource/
    ├── scripts/
    │   ├── install_service.sh
    │   └── start_multi_lidar.sh
    ├── systemd/
    │   └── multi-lidar.service.in
    ├── package.xml
    ├── setup.cfg
    ├── setup.py
    └── README.md

