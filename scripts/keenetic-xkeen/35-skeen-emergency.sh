#!/bin/sh
# Экстренное восстановление YouTube: VPS xray + полный сброс SKeen на роутере
# curl -fsSL http://193.233.232.48:8787/35-skeen-emergency.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"

echo "=== VPS xray restart ==="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' 2>/dev/null || true
sleep 2

/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2

conntrack -F 2>/dev/null || true
conntrack -D -p tcp --dport 8443 2>/dev/null || true

: > /opt/var/log/sing-box.log 2>/dev/null || true
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true

curl -fL -o /opt/etc/skeen/config/outbounds.json "$SKEEN_BASE/outbounds.json"
curl -fL -o /opt/etc/skeen/skeen.json "$SKEEN_BASE/skeen.json"
for f in route.json inbounds.json dns.json; do
  curl -fL -o "/opt/etc/skeen/config/$f" "$SKEEN_BASE/$f"
done
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config 2>/dev/null || true

iptables -C FORWARD -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true

/opt/bin/skeen start
sleep 5
conntrack -F 2>/dev/null || true

T=$(netstat -tn 2>/dev/null | grep ':8443' | wc -l)
/opt/bin/skeen status 2>/dev/null || true
echo "VPS tunnels=$T"
echo "ПК: ipconfig /flushdns, Ctrl+Shift+N -> youtube.com"
