#!/bin/bash
# Диагностика и быстрый фикс HA (туалет ZG-301Z + балкон SRW-TH01).
set -euo pipefail
EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -i ${HOME}/.ssh/id_ed25519"
SCP="scp ${SSH_OPTS} -P ${HA_SSH_PORT}"
SSH="ssh ${SSH_OPTS} -p ${HA_SSH_PORT} root@${HA_HOST}"

if [[ -f "${EMPIRE_DIR}/.env" ]]; then set -a && source "${EMPIRE_DIR}/.env" && set +a; fi

echo "==> scripts/tuya_srw_status.py → HA"
$SSH "mkdir -p /config/scripts"
$SCP "${EMPIRE_DIR}/homeassistant/scripts/tuya_srw_status.py" "root@${HA_HOST}:/config/scripts/"
$SSH "chmod +x /config/scripts/tuya_srw_status.py"

echo "==> ha_fix_now.py"
python3 "${EMPIRE_DIR}/tools/ha_fix_now.py" "$@"
