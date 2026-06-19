#!/bin/sh
# YouTube/Gmail мертвы: убрать блок QUIC, DNS xray -> IPv4, перезапуск
# curl -fsSL http://193.233.232.48:8787/12-fix-dead.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

curl -fL -o /opt/etc/xray/configs/02_dns.json "$BASE/02_dns.json"
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"
curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"

xkeen -stop 2>/dev/null || true
sleep 2
killall xray 2>/dev/null || true
sleep 1
xkeen -start
sleep 3
xkeen -status

echo ""
echo "=== DNS xray (должен быть UseIPv4) ==="
grep -E 'queryStrategy|1.1.1.1' /opt/etc/xray/configs/02_dns.json || true
echo ""
echo "=== routing: google + БЕЗ блока udp/443 ==="
grep -E 'google|443|youtubei' /opt/etc/xray/configs/05_routing.json | head -6
echo ""
echo "=== ПК ОБЯЗАТЕЛЬНО ==="
echo "1. IPv6 ВЫКЛ на сетевой карте"
echo "2. chrome://flags/#enable-quic -> Disabled"
echo "3. Chrome: Безопасный DNS -> Выкл"
echo "4. ipconfig /flushdns"
echo "5. Инкognito -> youtube.com + mail.google.com"
