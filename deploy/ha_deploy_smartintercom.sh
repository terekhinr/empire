#!/bin/bash
# SmartIntercom → ESPHome на HA + automations + dashboard.
#
#   cd /root/projects/empire && bash deploy/ha_deploy_smartintercom.sh
#
# Прошивка устройства — вручную (см. docs/HA_SMARTINTERCOM_ESPHOME.md):
#   BlueStreak OTA → esphome_1.7.6.esp32ota.bin, затем Install из ESPHome addon.

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_USER="${HA_USER:-root}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
HA_CONFIG="${HA_CONFIG:-/config}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -o StrictHostKeyChecking=no -i ${HOME}/.ssh/id_ed25519"
SCP_OPTS="${SSH_OPTS} -P ${HA_SSH_PORT}"
SSH_TARGET="${HA_USER}@${HA_HOST}"
ESPHOME_SRC="${EMPIRE_DIR}/homeassistant/esphome"
PYTHON="${EMPIRE_DIR}/venv/bin/python3"
[[ -x "${PYTHON}" ]] || PYTHON=python3

if [[ -f "${EMPIRE_DIR}/.env" ]]; then
  set -a && source "${EMPIRE_DIR}/.env" && set +a
fi

echo "==> SmartIntercom ESPHome → ${SSH_TARGET}"

ssh ${SSH_OPTS} -p "${HA_SSH_PORT}" "${SSH_TARGET}" "mkdir -p ${HA_CONFIG}/esphome/lib ${HA_CONFIG}/esphome/data ${HA_CONFIG}/packages"

# secrets: дописать ключи ESPHome если ещё нет
ssh ${SSH_OPTS} -p "${HA_SSH_PORT}" "${SSH_TARGET}" bash -s << 'REMOTE'
set -euo pipefail
SEC="/config/esphome/secrets.yaml"
touch "$SEC"
gen_hex32() { openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | xxd -p; }
if ! grep -q '^esphome_api_key:' "$SEC" 2>/dev/null; then
  echo "esphome_api_key: \"$(gen_hex32)$(gen_hex32)\"" >> "$SEC"
  echo "  secrets: добавлен esphome_api_key"
fi
if ! grep -q '^esphome_ota_password:' "$SEC" 2>/dev/null; then
  echo "esphome_ota_password: \"$(gen_hex32)\"" >> "$SEC"
  echo "  secrets: добавлен esphome_ota_password"
fi
REMOTE

echo "==> Копирование ESPHome проекта"
scp -r ${SCP_OPTS} \
  "${ESPHOME_SRC}/smartintercom-esp32.yaml" \
  "${ESPHOME_SRC}/partitions_esp32.csv" \
  "${ESPHOME_SRC}/card.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/esphome/"
scp -r ${SCP_OPTS} "${ESPHOME_SRC}/lib/"* "${SSH_TARGET}:${HA_CONFIG}/esphome/lib/"
scp -r ${SCP_OPTS} "${ESPHOME_SRC}/data/"* "${SSH_TARGET}:${HA_CONFIG}/esphome/data/"

echo "==> empire_domofon.yaml"
scp ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/packages/empire_domofon.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/packages/empire_domofon.yaml"

echo "==> Dashboard + yandex"
scp ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/dashboards/empire_main.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/dashboards/empire_main.yaml"
scp ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/yandex_smart_home.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/yandex_smart_home.yaml"

echo "==> Reload automations (API)"
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
for svc in ("script/reload", "automation/reload", "yandex_smart_home/reload"):
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
echo "Готово. Дальше в UI HA:"
echo "  1) ESPHome → smartintercom → Install (OTA с BlueStreak или USB)"
echo "  2) После ONLINE: FTP (anonymous) → загрузить *.mp3 из /config/esphome/data/ в корень"
echo "  3) Настройки → Устройства → SmartIntercom → область «Прихожая»"
echo "  4) Тест звонка → Telegram «Звонок в домофон!»"
echo ""
echo "Инструкция: docs/HA_SMARTINTERCOM_ESPHOME.md"
