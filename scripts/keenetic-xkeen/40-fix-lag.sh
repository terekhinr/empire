#!/bin/sh
# Убирает лаг: sniff 1500ms->200ms, Google IP до sniff, блок viewstats, таймауты
# curl -fsSL http://193.233.232.48:8787/40-fix-lag.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"

echo "========== 1. CONFIG =========="
for f in route.json inbounds.json outbounds.json; do
  curl -fL -o "/opt/etc/skeen/config/$f" "$SKEEN_BASE/$f"
done
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config 2>/dev/null || true

echo "========== 2. RESTART =========="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' 2>/dev/null || true
sleep 2
conntrack -F 2>/dev/null || true
conntrack -D -p tcp --dport 8443 2>/dev/null || true
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
: > /opt/var/log/sing-box.log 2>/dev/null || true
/opt/bin/skeen restart
sleep 4
/opt/bin/skeen status
echo "sniff=$(grep sniff /opt/etc/skeen/config/route.json | head -1)"
