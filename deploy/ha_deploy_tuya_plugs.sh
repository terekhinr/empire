#!/bin/bash
# Tuya розетки: новая на кухню, старая на балкон, расписание 05:30–01:00.
#
#   cd /root/projects/empire && bash deploy/ha_deploy_tuya_plugs.sh

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_USER="${HA_USER:-root}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
HA_CONFIG="${HA_CONFIG:-/config}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -o StrictHostKeyChecking=no -i ${HOME}/.ssh/id_ed25519"
SCP_OPTS="${SSH_OPTS} -P ${HA_SSH_PORT}"
SSH_CMD=(ssh ${SSH_OPTS} -p "${HA_SSH_PORT}")
SCP_CMD=(scp -q ${SCP_OPTS})
SSH_TARGET="${HA_USER}@${HA_HOST}"
PYTHON="${EMPIRE_DIR}/venv/bin/python3"
[[ -x "${PYTHON}" ]] || PYTHON=python3

if [[ -f "${EMPIRE_DIR}/.env" ]]; then
  set -a && source "${EMPIRE_DIR}/.env" && set +a
fi

echo "==> Скачать registry с ${SSH_TARGET}"
"${SCP_CMD[@]}" "${SSH_TARGET}:${HA_CONFIG}/.storage/core.config_entries" /tmp/ha_config_entries.json
"${SCP_CMD[@]}" "${SSH_TARGET}:${HA_CONFIG}/.storage/core.entity_registry" /tmp/ha_entity_registry.json
"${SCP_CMD[@]}" "${SSH_TARGET}:${HA_CONFIG}/.storage/core.device_registry" /tmp/ha_device_registry.json

echo "==> Патч LocalTuya + registry (без reload)"
HA_RELOAD=0 HA_CONFIG_ENTRIES=/tmp/ha_config_entries.json \
HA_ENTITY_REGISTRY=/tmp/ha_entity_registry.json \
HA_DEVICE_REGISTRY=/tmp/ha_device_registry.json \
  "${PYTHON}" "${EMPIRE_DIR}/tools/ha_tuya_plugs_setup.py"

echo "==> Загрузить registry и packages"
"${SCP_CMD[@]}" /tmp/ha_config_entries.json "${SSH_TARGET}:${HA_CONFIG}/.storage/core.config_entries"
"${SCP_CMD[@]}" /tmp/ha_entity_registry.json "${SSH_TARGET}:${HA_CONFIG}/.storage/core.entity_registry"
"${SCP_CMD[@]}" /tmp/ha_device_registry.json "${SSH_TARGET}:${HA_CONFIG}/.storage/core.device_registry"
"${SCP_CMD[@]}" \
  "${EMPIRE_DIR}/homeassistant/packages/empire_kuhnya_rozetka_schedule.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/packages/empire_kuhnya_rozetka_schedule.yaml"
"${SCP_CMD[@]}" \
  "${EMPIRE_DIR}/homeassistant/dashboards/empire_main.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/dashboards/empire_main.yaml"

echo "==> Reload LocalTuya + automations"
HA_RELOAD=1 HA_PATCH_ONLY=1 \
  "${PYTHON}" "${EMPIRE_DIR}/tools/ha_tuya_plugs_setup.py"

echo "==> Пост-обработка entity registry"
"${SCP_CMD[@]}" "${SSH_TARGET}:${HA_CONFIG}/.storage/core.entity_registry" /tmp/ha_entity_registry.json
"${SCP_CMD[@]}" "${SSH_TARGET}:${HA_CONFIG}/.storage/core.device_registry" /tmp/ha_device_registry.json
HA_RELOAD=0 HA_PATCH_ONLY=1 \
HA_ENTITY_REGISTRY=/tmp/ha_entity_registry.json \
HA_DEVICE_REGISTRY=/tmp/ha_device_registry.json \
HA_CONFIG_ENTRIES=/tmp/ha_config_entries.json \
  "${PYTHON}" "${EMPIRE_DIR}/tools/ha_tuya_plugs_setup.py"
"${SCP_CMD[@]}" /tmp/ha_entity_registry.json "${SSH_TARGET}:${HA_CONFIG}/.storage/core.entity_registry"
"${SCP_CMD[@]}" /tmp/ha_device_registry.json "${SSH_TARGET}:${HA_CONFIG}/.storage/core.device_registry"

echo "==> Переименовать entity (WebSocket)"
"${PYTHON}" "${EMPIRE_DIR}/tools/ha_tuya_plugs_setup.py" --rename

echo "==> Reload automations + yandex"
HA_URL="${HA_URL:-http://100.80.133.85:8123}" HA_TOKEN="${HA_TOKEN:-}" "${PYTHON}" - <<'PY'
import json, os, urllib.request
from pathlib import Path
env = Path("/root/projects/empire/.env")
token = os.environ.get("HA_TOKEN","")
url_base = os.environ.get("HA_URL","http://100.80.133.85:8123").rstrip("/")
if not token and env.exists():
    for line in env.read_text().splitlines():
        if line.startswith("HA_TOKEN="): token = line.split("=",1)[1]
        if line.startswith("HA_URL="): url_base = line.split("=",1)[1].strip().rstrip("/")
for svc in ("automation/reload", "yandex_smart_home/reload"):
    req = urllib.request.Request(
        f"{url_base}/api/services/{svc}", data=b"{}", method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"  {svc}: {r.status}")
    except Exception as e:
        print(f"  {svc}: {e}")
PY

echo ""
echo "Готово. Проверьте:"
echo "  switch.kuhnya_chainik (кухня, .143) — расписание 05:30–01:00"
echo "  switch.balkon_multivarka (балкон, .40) — offline пока не включена на балконе"
echo "  Закрепите IP в роутере: NEW MAC 70:89:76:35:8e:16 → .143, OLD MAC 1c:90:ff:a5:50:e7 → .40"
