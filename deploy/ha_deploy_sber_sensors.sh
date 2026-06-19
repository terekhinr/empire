#!/bin/bash
# Sber Zigbee SBDV-00079 + SBDV-00030 → ZHA.
#
#   cd /root/projects/empire
#   bash deploy/ha_deploy_sber_sensors.sh
#
# После запуска: сбросьте оба датчика (кнопка → мигание), держите у координатора.

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_USER="${HA_USER:-root}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
HA_CONFIG="${HA_CONFIG:-/config}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -o StrictHostKeyChecking=no -i ${HOME}/.ssh/id_ed25519"
SCP_OPTS="${SSH_OPTS} -P ${HA_SSH_PORT}"
SSH_CMD="ssh ${SSH_OPTS} -p ${HA_SSH_PORT}"
SCP_CMD="scp -q ${SCP_OPTS}"
SSH_TARGET="${HA_USER}@${HA_HOST}"

if [[ -f "${EMPIRE_DIR}/.env" ]]; then
  set -a && source "${EMPIRE_DIR}/.env" && set +a
fi

PYTHON="${EMPIRE_DIR}/venv/bin/python3"
[[ -x "${PYTHON}" ]] || PYTHON=python3

echo "==> Empire → Sber sensors (${SSH_TARGET})"

if ${SSH_CMD} "${SSH_TARGET}" "mkdir -p ${HA_CONFIG}/packages"; then
  ${SCP_CMD} \
    "${EMPIRE_DIR}/homeassistant/packages/empire_sber_sensors.yaml" \
    "${SSH_TARGET}:${HA_CONFIG}/packages/empire_sber_sensors.yaml"
  ${SCP_CMD} \
    "${EMPIRE_DIR}/homeassistant/packages/empire_telegram.yaml" \
    "${SSH_TARGET}:${HA_CONFIG}/packages/empire_telegram.yaml" 2>/dev/null || true
  echo "packages скопированы"
else
  echo "SSH недоступен — копируйте packages/empire_sber_sensors.yaml вручную в /config/packages/"
fi

echo "==> Reload automations"
HA_URL="${HA_URL:-http://${HA_HOST}:8123}"
curl -sf -X POST -H "Authorization: Bearer ${HA_TOKEN}" -H "Content-Type: application/json" \
  "${HA_URL}/api/services/automation/reload" >/dev/null || true

echo "==> ZHA permit 240 с + ожидание датчиков (до 5 мин)"
echo "    Сброс: кнопка на датчике → мигание. Датчики — в 1 м от Sonoff Dongle."
"${PYTHON}" "${EMPIRE_DIR}/tools/ha_sber_sensors_setup.py" wait --duration 240 --timeout 300 || \
  "${PYTHON}" "${EMPIRE_DIR}/tools/ha_sber_sensors_setup.py" configure || true

echo ""
echo "Проверка entity:"
curl -sf -H "Authorization: Bearer ${HA_TOKEN}" "${HA_URL}/api/states" | \
  "${PYTHON}" -c "
import sys, json
want = ('sber_th', 'sber_otkrytie', 'sbdv')
for s in json.load(sys.stdin):
    e = s['entity_id']
    if any(w in e for w in want):
        print(' ', e, '=', s['state'])
" || true

echo "Готово."
