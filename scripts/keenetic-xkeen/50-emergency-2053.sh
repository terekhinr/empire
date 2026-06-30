#!/bin/sh
# Аварийный фикс: только порт 2053, полный сброс.
# curl -fsSL http://193.233.232.48:8787/50-emergency-2053.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="http://193.233.232.48:8787"
SKEEN="$BASE/skeen"

curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' || true
sleep 3

for f in route.json outbounds.json; do
  curl -fL -o "/opt/etc/skeen/config/$f" "$SKEEN/$f"
done
curl -fL -o /opt/etc/skeen/watchdog.sh "$SKEEN/watchdog.sh"
chmod +x /opt/etc/skeen/watchdog.sh
/opt/bin/skeen-box check -D /opt/etc/skeen -C /opt/etc/skeen/config

iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true

/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2
conntrack -D -p tcp --dst 193.233.232.48 2>/dev/null || true
conntrack -D -p tcp --dport 2053 2>/dev/null || true
conntrack -D -p tcp --dport 8443 2>/dev/null || true
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
: > /opt/var/log/sing-box.log
/opt/bin/skeen start
sleep 12

echo "errors:" $(grep -c ERROR /opt/var/log/sing-box.log 2>/dev/null || echo 0)
grep -i youtube /opt/var/log/sing-box.log | tail -4 || true
/opt/bin/skeen status | head -3
