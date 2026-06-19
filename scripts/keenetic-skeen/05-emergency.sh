#!/bin/sh
# Аварийный сброс: чистые туннели, без watchdog, только TCP redirect.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_SKEEN_BASE:-http://193.233.232.48:8787/skeen}"

echo "=== STOP ==="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2

echo "=== FLUSH TUNNELS ==="
conntrack -D -p tcp --dport 8443 2>/dev/null || true
conntrack -D -p tcp --dst 193.233.232.48 2>/dev/null || true
netstat -tn 2>/dev/null | grep ':8443' | wc -l | xargs echo "left:"

echo "=== CONFIG ==="
curl -fL -o /opt/etc/skeen/skeen.json "$BASE/skeen.json"
for f in inbounds.json outbounds.json route.json; do
  curl -fL -o /opt/etc/skeen/config/$f "$BASE/$f"
done
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config
/opt/bin/skeen-box check -D /opt/etc/skeen -C /opt/etc/skeen/config

echo "=== DISABLE WATCHDOG (мешает) ==="
crontab -l 2>/dev/null | grep -v skeen/watchdog | crontab - 2>/dev/null || true

echo "=== START ==="
/opt/bin/skeen start
sleep 8
/opt/bin/skeen status
netstat -tn 2>/dev/null | grep ':8443' | wc -l | xargs echo "tunnels:"

echo ""
echo "Подожди 30 сек, потом YouTube в инкognito."
echo "Политика SKeen: ТОЛЬКО Destroy_ + СберТелек!"
