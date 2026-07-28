#!/usr/bin/env bash

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "❌ sudo로 실행해야 합니다."
    echo "사용법: sudo bash scripts/install_service.sh"
    exit 1
fi

INSTALL_USER="${SUDO_USER:-}"

if [[ -z "${INSTALL_USER}" || "${INSTALL_USER}" == "root" ]]; then
    echo "❌ 일반 사용자 계정에서 sudo를 사용해 실행해주세요."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_DIR="$(cd "${PACKAGE_DIR}/../.." && pwd)"

START_SCRIPT="${PACKAGE_DIR}/scripts/start_multi_lidar.sh"
SERVICE_TEMPLATE="${PACKAGE_DIR}/systemd/multi-lidar.service.in"
SERVICE_FILE="/etc/systemd/system/multi-lidar.service"

USER_HOME="$(getent passwd "${INSTALL_USER}" | cut -d: -f6)"

if [[ ! -f "${WORKSPACE_DIR}/install/setup.bash" ]]; then
    echo "❌ ROS2 워크스페이스가 빌드되지 않았습니다."
    echo "먼저 워크스페이스에서 colcon build를 실행해주세요."
    exit 1
fi

chmod 755 "${START_SCRIPT}"

if ! id -nG "${INSTALL_USER}" | tr ' ' '\n' | grep -qx dialout; then
    usermod -aG dialout "${INSTALL_USER}"
    echo "ℹ️ ${INSTALL_USER} 사용자를 dialout 그룹에 추가했습니다."
fi

sed \
    -e "s|@USER@|${INSTALL_USER}|g" \
    -e "s|@HOME@|${USER_HOME}|g" \
    -e "s|@WORKSPACE@|${WORKSPACE_DIR}|g" \
    -e "s|@START_SCRIPT@|${START_SCRIPT}|g" \
    "${SERVICE_TEMPLATE}" \
    > "${SERVICE_FILE}"

systemctl daemon-reload
systemctl enable --now multi-lidar.service

echo
echo "✅ multi-lidar.service 설치 및 자동 실행 등록 완료"
systemctl status multi-lidar.service --no-pager -l || true
