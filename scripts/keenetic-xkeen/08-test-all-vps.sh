#!/bin/sh
# Диагностика: весь трафик XKeen через VPS. Если YouTube заработает — проблема в routing-списках.
# Откат: curl -fsSL http://193.233.232.48:8787/07-fix-youtube.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

cp -a /opt/etc/xray/configs/05_routing.json /opt/etc/xray/configs/05_routing.json.pre-test 2>/dev/null || true
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing_all_vps.json"
xkeen -restart
echo "=== TEST MODE: ALL -> vless-reality ==="
xkeen -status
echo "Открой YouTube на ПК. Откат: sh /tmp/xkeen/07-fix-youtube.sh или curl .../07-fix-youtube.sh | sh"
