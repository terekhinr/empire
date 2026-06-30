#!/bin/bash
# Балкон SRW-TH01: деплой локального опроса + discover в LAN.
set -euo pipefail
EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -i ${HOME}/.ssh/id_ed25519"
SCP="scp ${SSH_OPTS} -P ${HA_SSH_PORT}"
SSH="ssh ${SSH_OPTS} -p ${HA_SSH_PORT} root@${HA_HOST}"
PYTHON="${EMPIRE_DIR}/venv/bin/python3"
[[ -x "${PYTHON}" ]] || PYTHON=python3

if [[ -f "${EMPIRE_DIR}/.env" ]]; then set -a && source "${EMPIRE_DIR}/.env" && set +a; fi

echo "==> scripts + package → HA"
$SSH "mkdir -p /config/scripts /config/packages"
$SCP "${EMPIRE_DIR}/homeassistant/scripts/tuya_srw_status.py" "root@${HA_HOST}:/config/scripts/"
$SCP "${EMPIRE_DIR}/homeassistant/packages/empire_balkon_srw_th01.yaml" "root@${HA_HOST}:/config/packages/"
$SSH "chmod +x /config/scripts/tuya_srw_status.py"

echo "==> reload + restart HA core (новые command_line)"
$SSH "ha core restart"
echo "==> wait core"
sleep 75

echo "==> discover"
"${PYTHON}" "${EMPIRE_DIR}/tools/ha_balkon_srw_setup.py" "$@"
