#!/bin/bash
# Кухня + туалет → HA (Tailscale).
#
#   cd /root/projects/empire && bash deploy/ha_deploy_kitchen.sh

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_USER="${HA_USER:-root}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
HA_CONFIG="${HA_CONFIG:-/config}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -o StrictHostKeyChecking=no -i ${HOME}/.ssh/id_ed25519"
SCP_OPTS="${SSH_OPTS} -P ${HA_SSH_PORT}"
SSH_TARGET="${HA_USER}@${HA_HOST}"
PYTHON="${EMPIRE_DIR}/venv/bin/python3"
[[ -x "${PYTHON}" ]] || PYTHON=python3

if [[ -f "${EMPIRE_DIR}/.env" ]]; then
  set -a && source "${EMPIRE_DIR}/.env" && set +a
fi

echo "==> PIR → Zbeacon отвязка (API)"
python3 "${EMPIRE_DIR}/tools/ha_kitchen_unbind_pir.py" || true

echo "==> Копирование packages + yandex → ${SSH_TARGET}"
ssh ${SSH_OPTS} -p "${HA_SSH_PORT}" "${SSH_TARGET}" "mkdir -p ${HA_CONFIG}/packages"

scp ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/packages/empire_kuhnya_zbeacon.yaml" \
  "${EMPIRE_DIR}/homeassistant/packages/empire_tualet_hobeian.yaml" \
  "${EMPIRE_DIR}/homeassistant/packages/empire_motion_pir_koridor.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/packages/"

scp ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/yandex_smart_home.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/yandex_smart_home.yaml"

echo "==> Reload HA services"
HA_URL="${HA_URL:-http://100.80.133.85:8123}" HA_TOKEN="${HA_TOKEN:-}" "${PYTHON}" - <<'PY'
import json, os, urllib.request
from pathlib import Path
env = Path("/root/projects/empire/.env")
token = os.environ.get("HA_TOKEN", "")
url_base = os.environ.get("HA_URL", "http://100.80.133.85:8123").rstrip("/")
if not token and env.exists():
    for line in env.read_text().splitlines():
        if line.startswith("HA_TOKEN="):
            token = line.split("=", 1)[1]
for svc in ("script/reload", "automation/reload", "template/reload", "yandex_smart_home/reload"):
    req = urllib.request.Request(
        f"{url_base}/api/services/{svc}",
        data=b"{}",
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"  {svc}: {r.status}")
PY

echo ""
echo "Готово. В «Дом с Алисой» → Yaha Cloud → Обновить список устройств."
echo "Кухня: «включи свет на кухне». Туалет: «включи свет в туалете»."
echo "Если Zbeacon всё ещё глючит — Zigbee-роутер у кухни: docs/HA_KITCHEN_ZBEACON.md"
