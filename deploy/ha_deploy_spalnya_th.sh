#!/bin/bash
# Спальня T/H _TZE284_hodyryli: ZHA quirk + template sensors + дашборды.
#
#   cd /root/projects/empire && bash deploy/ha_deploy_spalnya_th.sh

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
HA_CONFIG="${HA_CONFIG:-/config}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -o StrictHostKeyChecking=no -i ${HOME}/.ssh/id_ed25519"
SCP_OPTS="${SSH_OPTS} -P ${HA_SSH_PORT}"
SSH_CMD="ssh ${SSH_OPTS} -p ${HA_SSH_PORT}"
PYTHON="${EMPIRE_DIR}/venv/bin/python3"
[[ -x "${PYTHON}" ]] || PYTHON=python3

if [[ -f "${EMPIRE_DIR}/.env" ]]; then set -a && source "${EMPIRE_DIR}/.env" && set +a; fi

SSH_TARGET="root@${HA_HOST}"

echo "==> ZHA quirk + package + dashboards → ${SSH_TARGET}"
${SSH_CMD} "${SSH_TARGET}" "mkdir -p ${HA_CONFIG}/custom_zha_quirks ${HA_CONFIG}/packages ${HA_CONFIG}/dashboards"
scp -q ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/custom_zha_quirks/tze284_hodyryli_th.py" \
  "${SSH_TARGET}:${HA_CONFIG}/custom_zha_quirks/tze284_hodyryli_th.py"
scp -q ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/packages/empire_spalnya_th.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/packages/empire_spalnya_th.yaml"
scp -q ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/dashboards/empire_wall.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/dashboards/empire_wall.yaml"
scp -q ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/dashboards/empire_main.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/dashboards/empire_main.yaml"

${SSH_CMD} "${SSH_TARGET}" bash -s << 'REMOTE'
set -euo pipefail
CFG="/config/configuration.yaml"
if [[ -f "$CFG" ]] && ! grep -q 'custom_quirks_path' "$CFG" 2>/dev/null; then
  printf '\n# ZHA custom quirks (Empire)\nzha:\n  custom_quirks_path: /config/custom_zha_quirks\n' >> "$CFG"
  echo "configuration.yaml: добавлен custom_quirks_path"
fi
REMOTE

echo "==> HA core restart (quirk)"
${SSH_CMD} "${SSH_TARGET}" "ha core restart"
echo "==> wait core"
sleep 75

echo "==> ZHA reconfigure + template reload"
"${PYTHON}" "${EMPIRE_DIR}/tools/ha_spalnya_th_setup.py"

echo ""
echo "Готово. Проверка:"
echo "  sensor.spalnya_temperatura / sensor.spalnya_temperatura_ulica"
echo "  /empire-wall/dom и /empire-wall/klima"
