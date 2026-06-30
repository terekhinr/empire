#!/bin/bash
# Teckin TC100 → Generic Camera (config flow, без YAML platform: generic).
#
#   cd /root/projects/empire && bash deploy/ha_deploy_teckin_tc100.sh

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_USER="${HA_USER:-root}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
HA_CONFIG="${HA_CONFIG:-/config}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -o StrictHostKeyChecking=no -i ${HOME}/.ssh/id_ed25519"
SSH_TARGET="${HA_USER}@${HA_HOST}"
PYTHON="${PYTHON:-python3}"

# Убрать устаревший YAML (вызывает repair «Unused YAML configuration for generic»)
echo "==> Удаление empire_teckin_tc100.yaml с HA"
ssh ${SSH_OPTS} -p "${HA_SSH_PORT}" "${SSH_TARGET}" \
  "rm -f ${HA_CONFIG}/packages/empire_teckin_tc100.yaml"

echo "==> Generic Camera через config flow"
set -a
# shellcheck disable=SC1091
[ -f "${EMPIRE_DIR}/.env" ] && source "${EMPIRE_DIR}/.env"
set +a
HA_URL="${HA_URL:-http://100.80.133.85:8123}" HA_TOKEN="${HA_TOKEN:-}" \
  "${PYTHON}" "${EMPIRE_DIR}/tools/ha_teckin_tc100_setup.py"

echo "Готово: camera.teckin_tc100 → rtsp://192.168.1.84:554/video0_unicast"
