#!/bin/sh
# Убирает лаг v2: политика SKeen (только нужные устройства), только :443, без vision EOF
# curl -fsSL http://193.233.232.48:8787/41-fix-lag-v2.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"

echo "========== 1. VPS xray (no vision) =========="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' || true
sleep 3

echo "========== 2. SKeen CONFIG =========="
curl -fL -o /opt/etc/skeen/skeen.json "$SKEEN_BASE/skeen.json"
for f in route.json inbounds.json outbounds.json; do
  curl -fL -o "/opt/etc/skeen/config/$f" "$SKEEN_BASE/$f"
done
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config 2>/dev/null || true

echo "========== 3. RESTART =========="
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
: > /opt/var/log/sing-box.log 2>/dev/null || true
/opt/bin/skeen restart
sleep 5
/opt/bin/skeen status
grep -E 'enable|port' /opt/etc/skeen/skeen.json | head -6

echo ""
echo "ВАЖНО в Keenetic Web:"
echo "  Политика Keenetic должна называться «Singbox» (Destroy_ + СберТелек)"
echo "  Transmission на роутере — пауза (жрёт 25% CPU)"
