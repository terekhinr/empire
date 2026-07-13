#!/bin/bash
# Teckin кухня: go2rtc rotate 180° + generic → локальный поток.
set -euo pipefail
EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -i ${HOME}/.ssh/id_ed25519"
ENTRY_ID="01KVWABNDDHAQ09RB9A3HSV9ZY"

echo "==> go2rtc.yaml"
scp ${SSH_OPTS} -P "${HA_SSH_PORT}" \
  "${EMPIRE_DIR}/homeassistant/go2rtc.yaml" \
  "root@${HA_HOST}:/config/go2rtc.yaml"

echo "==> generic stream → go2rtc teckin_kuhnya"
TMP="/tmp/ha_ce_teckin_rotate.json"
scp ${SSH_OPTS} -P "${HA_SSH_PORT}" "root@${HA_HOST}:/config/.storage/core.config_entries" "${TMP}"
python3 - "${TMP}" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
ce = json.loads(path.read_text())
for e in ce["data"]["entries"]:
    if e.get("entry_id") != "01KVWABNDDHAQ09RB9A3HSV9ZY":
        continue
    opts = e.setdefault("options", {})
    opts["stream_source"] = "rtsp://127.0.0.1:8554/teckin_kuhnya"
    opts["still_image_url"] = "http://127.0.0.1:1984/api/frame.jpeg?src=teckin_kuhnya"
    opts.setdefault("advanced", {})
    opts["advanced"]["rtsp_transport"] = "tcp"
    print("updated stream_source + still_image_url")
path.write_text(json.dumps(ce, indent=2))
PY
scp ${SSH_OPTS} -P "${HA_SSH_PORT}" "${TMP}" "root@${HA_HOST}:/config/.storage/core.config_entries"

echo "==> dashboard"
scp ${SSH_OPTS} -P "${HA_SSH_PORT}" \
  "${EMPIRE_DIR}/homeassistant/dashboards/empire_wall.yaml" \
  "root@${HA_HOST}:/config/dashboards/empire_wall.yaml"

echo "==> restart HA core (go2rtc + generic)"
ssh ${SSH_OPTS} -p "${HA_SSH_PORT}" "root@${HA_HOST}" "ha core restart"
echo "Готово. Через ~2 мин: /empire-wall/kamery → Кухня"
