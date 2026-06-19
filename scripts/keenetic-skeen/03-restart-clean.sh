#!/bin/sh
# Перезапуск sing-box + сброс зависших туннелей. Раз в сутки или при отвале YouTube.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_SKEEN_BASE:-http://193.233.232.48:8787/skeen}"

curl -fL -o /opt/etc/skeen/config/outbounds.json "$BASE/outbounds.json"
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config

echo "=== tunnels before ==="
netstat -tn 2>/dev/null | grep ':8443' | wc -l

/opt/bin/skeen restart
sleep 3

echo "=== tunnels after ==="
netstat -tn 2>/dev/null | grep ':8443' | wc -l
/opt/bin/skeen status

echo "OK. YouTube: Ctrl+Shift+N"
