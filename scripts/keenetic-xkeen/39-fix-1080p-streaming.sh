#!/bin/sh
# 1080p YouTube: буферы VPS + сброс туннелей + свежий outbound
# curl -fsSL http://193.233.232.48:8787/39-fix-1080p-streaming.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"

echo "========== 1. VPS xray (buffer 512KB) =========="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' || true
sleep 4

echo "========== 2. SKeen outbound =========="
curl -fL -o /opt/etc/skeen/config/outbounds.json "$SKEEN_BASE/outbounds.json"
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config 2>/dev/null || true

echo "========== 3. CLEAN RESTART =========="
conntrack -F 2>/dev/null || true
conntrack -D -p tcp --dport 8443 2>/dev/null || true
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
/opt/bin/skeen restart
sleep 5

echo "========== 4. STATUS =========="
/opt/bin/skeen status 2>/dev/null || true
T=$(netstat -tn 2>/dev/null | grep ':8443' | wc -l)
echo "VPS tunnels=$T (норма <10)"
echo ""
echo "Проверка: YouTube -> качество 1080p, Ctrl+Shift+N если с ПК"
