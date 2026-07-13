#!/bin/bash
# Кухня Teckin: восстановить поток + card-mod + поворот 180° на карточке.
set -euo pipefail
EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -i ${HOME}/.ssh/id_ed25519"
SSH="ssh ${SSH_OPTS} -p ${HA_SSH_PORT} root@${HA_HOST}"
SCP="scp ${SSH_OPTS} -P ${HA_SSH_PORT}"

echo "==> 1) Вернуть прямой RTSP (без go2rtc loop)"
TMP="/tmp/ha_ce_teckin_fix.json"
$SCP "root@${HA_HOST}:/config/.storage/core.config_entries" "${TMP}"
python3 - "${TMP}" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
ce = json.loads(path.read_text())
for e in ce["data"]["entries"]:
    if e.get("entry_id") != "01KVWABNDDHAQ09RB9A3HSV9ZY":
        continue
    opts = e.setdefault("options", {})
    opts["stream_source"] = "rtsp://192.168.1.34:554/video0_unicast"
    opts["still_image_url"] = "https://192.168.1.34/cgi-bin/currentpic.cgi"
    print("restored direct RTSP .34")
path.write_text(json.dumps(ce, indent=2))
PY
$SCP "${TMP}" "root@${HA_HOST}:/config/.storage/core.config_entries"

echo "==> 2) Установить card-mod (без него CSS не работал)"
$SSH "mkdir -p /config/www/community/lovelace-card-mod && \
  curl -fsSL -o /config/www/community/lovelace-card-mod/card-mod.js \
  https://raw.githubusercontent.com/thomasloven/lovelace-card-mod/v4.2.1/card-mod.js"

CFG_TMP="/tmp/ha_configuration_cardmod.yaml"
$SCP "root@${HA_HOST}:/config/configuration.yaml" "${CFG_TMP}"
python3 - "${CFG_TMP}" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
text = p.read_text()
needle = "/local/community/lovelace-card-mod/card-mod.js"
if needle in text:
    print("card-mod already in configuration.yaml")
    raise SystemExit(0)
block = """  resources:
    - url: /local/community/lovelace-card-mod/card-mod.js
      type: module
"""
if "lovelace:" not in text:
    text = text.rstrip() + f"\nlovelace:\n{block}\n"
else:
    m = re.search(r"^lovelace:\n", text, re.M)
    if not m:
        raise SystemExit("lovelace: block not found")
    insert_at = m.end()
    rest = text[insert_at:]
    next_top = re.search(r"^[A-Za-z#]", rest, re.M)
    end = insert_at + (next_top.start() if next_top else len(rest))
    chunk = text[insert_at:end]
    if "resources:" in chunk:
        chunk = chunk.rstrip() + "\n    - url: /local/community/lovelace-card-mod/card-mod.js\n      type: module\n"
    else:
        chunk = chunk.rstrip() + "\n" + block
    text = text[:insert_at] + chunk + text[end:]
p.write_text(text)
print("card-mod resource merged into lovelace block")
PY
$SCP "${CFG_TMP}" "root@${HA_HOST}:/config/configuration.yaml"

echo "==> 3) dashboard + go2rtc (rotate source, на будущее)"
$SCP "${EMPIRE_DIR}/homeassistant/go2rtc.yaml" "root@${HA_HOST}:/config/go2rtc.yaml"
$SCP "${EMPIRE_DIR}/homeassistant/dashboards/empire_wall.yaml" "root@${HA_HOST}:/config/dashboards/empire_wall.yaml"

echo "==> 4) restart HA"
$SSH "ha core restart"
echo "Готово. Ctrl+F5 → /empire-wall/kamery"
