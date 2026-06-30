#!/bin/bash
# SRW-TH01: LocalTuya + template sensors (без облачного command_line).
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

echo "==> scripts + package → HA"
$SSH "mkdir -p /config/scripts /config/packages"
$SCP "${EMPIRE_DIR}/homeassistant/scripts/tuya_srw_fetch_key.py" "root@${HA_HOST}:/config/scripts/"
$SCP "${EMPIRE_DIR}/homeassistant/packages/empire_balkon_srw_th01.yaml" "root@${HA_HOST}:/config/packages/"
$SSH "chmod +x /config/scripts/tuya_srw_fetch_key.py"

echo "==> reload core (shell_command + template)"
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/homeassistant/reload_core_config" -d '{}' >/dev/null
sleep 8

echo "==> fetch local_key (Tuya Cloud, разово)"
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/shell_command/balkon_srw_fetch_key" -d '{}' >/dev/null || true
sleep 4
$SCP "root@${HA_HOST}:/config/scripts/.srw_local.json" "${EMPIRE_DIR}/.srw_local.json" 2>/dev/null || true

echo "==> LocalTuya patch"
$SCP "root@${HA_HOST}:/config/.storage/core.config_entries" /tmp/ha_config_entries.json
$SCP "root@${HA_HOST}:/config/.storage/core.entity_registry" /tmp/ha_entity_registry.json
HA_CONFIG_ENTRIES=/tmp/ha_config_entries.json \
HA_ENTITY_REGISTRY=/tmp/ha_entity_registry.json \
"${PYTHON}" "${EMPIRE_DIR}/tools/ha_balkon_srw_localtuya.py"
$SCP /tmp/ha_config_entries.json "root@${HA_HOST}:/config/.storage/core.config_entries"
$SCP /tmp/ha_entity_registry.json "root@${HA_HOST}:/config/.storage/core.entity_registry"

echo "==> reload LocalTuya + restart + template"
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/homeassistant/reload_config_entry" \
  -d '{"entry_id":"01F1XRJS41AC54X2WPAEHVBMS1"}' >/dev/null
$SSH "ha core restart"
sleep 80
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/template/reload" -d '{}' >/dev/null

echo ""
echo "Готово. Нажмите кнопку на датчике балкона — первое обновление после сна."
