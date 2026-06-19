#!/bin/sh
# СТАБИЛЬНЫЙ откат: конфиг когда YouTube работал + Google/Gmail. Без IPIfNonMatch.
# curl -fsSL http://193.233.232.48:8787/14-stable.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

rm -f /opt/etc/xray/configs/05_routing.json.bak
rm -f /opt/etc/xray/configs/05_routing.json.pre-test

/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

curl -fL -o /opt/etc/xray/configs/02_dns.json "$BASE/02_dns.json"
curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"

xkeen -stop 2>/dev/null || true
sleep 2
killall xray 2>/dev/null || true
sleep 1
xkeen -start
sleep 3

xkeen -status
echo ""
grep -q '"domainStrategy".*IPIfNonMatch' /opt/etc/xray/configs/05_routing.json && echo "WARN: IPIfNonMatch в routing!" || echo "OK: routing стабильный"
grep "udp.*443\|port.*443" /opt/etc/xray/configs/05_routing.json | head -2 || true
echo ""
echo "=== ПК ==="
echo "1. IPv6 ВЫКЛ"
echo "2. chrome://flags/#enable-quic -> Disabled"
echo "3. AdGuard ВЫКЛ"
echo "4. ipconfig /flushdns"
echo "5. curl -I https://www.youtube.com  (должен HTTP/2 200)"
echo ""
echo "Если curl 200, а Chrome нет -> виноват Chrome/расширения."
echo "Если curl timeout -> Keenetic: ПК в политике XKeen."
