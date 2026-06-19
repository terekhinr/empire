#!/bin/sh
# YouTube fix: stop nfqws conflict, update routing (QUIC block + CDN domains), restart XKeen.
# curl -fsSL http://193.233.232.48:8787/07-fix-youtube.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

echo "=== 1. Остановка nfqws / zapret (конфликт с XKeen) ==="
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
/opt/etc/init.d/S99zapret2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

echo "=== 2. Обновление routing + outbound с VPS ==="
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"
curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"

echo "=== 3. Перезапуск XKeen ==="
xkeen -restart

echo ""
echo "=== 4. Статус ==="
xkeen -status 2>/dev/null || true
grep -E 'google|youtube|ytimg|domainStrategy' /opt/etc/xray/configs/05_routing.json | head -10
echo "NFQUEUE=$(iptables-save 2>/dev/null | grep -c NFQUEUE || echo 0)"
echo ""
echo "ПК: timestamps + QUIC off + инкогнито БЕЗ расширений."
echo "НЕ запускай 08-test-all-vps — роутер не тянет весь трафик через VPS."
