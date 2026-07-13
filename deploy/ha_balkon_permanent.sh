#!/bin/bash
# Балкон SRW: постоянная схема LocalTuya + template + auto-discover IP.
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
HA_URL="${HA_URL:-http://100.80.133.85:8123}"

echo "==> scripts + package + tinytuya_pkg"
$SSH "mkdir -p /config/scripts/tinytuya_pkg /config/packages"
$SCP "${EMPIRE_DIR}/homeassistant/scripts/tuya_srw_status.py" "root@${HA_HOST}:/config/scripts/"
$SCP "${EMPIRE_DIR}/homeassistant/scripts/tuya_srw_sync_localtuya.py" "root@${HA_HOST}:/config/scripts/"
$SCP -r "${EMPIRE_DIR}/homeassistant/scripts/tinytuya_pkg" "root@${HA_HOST}:/config/scripts/" 2>/dev/null || true
$SCP "${EMPIRE_DIR}/homeassistant/packages/empire_balkon_srw_th01.yaml" "root@${HA_HOST}:/config/packages/"

echo "==> LocalTuya: local_key из .srw_local.json"
$SCP "root@${HA_HOST}:/config/.storage/core.config_entries" /tmp/ha_ce_balkon.json
$SCP "root@${HA_HOST}:/config/scripts/.srw_local.json" "${EMPIRE_DIR}/.srw_local.json" 2>/dev/null || true
HA_CONFIG_ENTRIES=/tmp/ha_ce_balkon.json HA_SKIP_RELOAD=1 \
  "${PYTHON}" "${EMPIRE_DIR}/tools/ha_balkon_srw_localtuya.py" || true
$SCP /tmp/ha_ce_balkon.json "root@${HA_HOST}:/config/.storage/core.config_entries"

echo "==> restart HA (убрать command_line, включить template+automation)"
$SSH "ha core restart"
echo "ждём 80с…"
sleep 80

echo "==> discover + sync LocalTuya IP"
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/shell_command/balkon_srw_discover" -d '{}' || true
sleep 15
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/shell_command/balkon_srw_sync_localtuya" -d '{}' || true
sleep 3
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/homeassistant/reload_config_entry" \
  -d '{"entry_id":"01F1XRJS41AC54X2WPAEHVBMS1"}' || true
sleep 10
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/template/reload" -d '{}' || true

echo ""
"${PYTHON}" "${EMPIRE_DIR}/tools/ha_health_check.py" | grep -E 'Балкон|Итого' || true
echo ""
echo "Готово. Если балкон offline — один раз нажмите кнопку на SRW; дальше discover каждые 6ч."
echo "Рекомендация: в Keenetic закрепите DHCP для SRW (MAC на наклейке датчика)."
