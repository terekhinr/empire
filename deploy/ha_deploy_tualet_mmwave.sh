#!/bin/bash
# Tuya mmWave _TZE204_qasjif9e: custom quirk + re-pair.
set -euo pipefail
EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
SSH_OPTS="-o ConnectTimeout=15 -i ${HOME}/.ssh/id_ed25519"
SSH="ssh ${SSH_OPTS} -p ${HA_SSH_PORT} root@${HA_HOST}"
SCP="scp ${SSH_OPTS} -P ${HA_SSH_PORT}"
HA_CONFIG="/homeassistant"
IEEE="a4:c1:38:64:a8:6e:7a:4d"

echo "==> quirk + packages"
$SSH "mkdir -p ${HA_CONFIG}/custom_zha_quirks"
$SCP "${EMPIRE_DIR}/homeassistant/custom_zha_quirks/ts0601_qasjif9e.py" \
  "root@${HA_HOST}:${HA_CONFIG}/custom_zha_quirks/"
$SCP "${EMPIRE_DIR}/homeassistant/packages/empire_motion_light_tualet.yaml" \
  "root@${HA_HOST}:${HA_CONFIG}/packages/"

$SSH "rm -rf ${HA_CONFIG}/custom_zha_quirks/__pycache__"
echo "==> restart HA core (quirk load)"
$SSH "ha core restart"
echo "==> wait core"
sleep 90

if [[ -f "${EMPIRE_DIR}/.env" ]]; then set -a && source "${EMPIRE_DIR}/.env" && set +a; fi
echo "==> remove old device"
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/zha/remove" -d "{\"ieee\":\"${IEEE}\"}" || true
sleep 5
echo "==> permit 180s — нажми кнопку на датчике 5-10 с"
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/zha/permit" -d '{"duration":180}'
echo ""
echo "Готово. После спаривания: python3 tools/ha_sensors_fix.py"
