#!/bin/sh
# Полный откат YouTube/XKeen после экспериментов (all-vps, IPIfNonMatch, битый .bak)
# curl -fsSL http://193.233.232.48:8787/10-youtube-recovery.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

echo "=== 1. Остановка nfqws/zapret ==="
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
/opt/etc/init.d/S99zapret2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

echo "=== 2. Удаление битых backup routing ==="
rm -f /opt/etc/xray/configs/05_routing.json.bak
rm -f /opt/etc/xray/configs/05_routing.json.pre-test

echo "=== 3. Заводской routing + outbound с VPS ==="
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing_factory.json"
curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"

echo "=== 4. Перезапуск XKeen ==="
xkeen -stop 2>/dev/null || true
sleep 2
killall xray 2>/dev/null || true
sleep 1
xkeen -start
sleep 3

echo ""
echo "=== 5. Статус ==="
xkeen -status 2>/dev/null || ps w | grep xray | grep -v grep
echo ""
grep -E 'geosite_zkeen|geoip_zkeen|443' /opt/etc/xray/configs/05_routing.json | head -6
echo ""
echo "Соединения VPS (открой YouTube на ПК, потом снова эту команду):"
netstat -an 2>/dev/null | grep 8443 | head -5 || true
echo ""
echo "=== ПК (обязательно) ==="
echo "1. Инкognito, без расширений"
echo "2. chrome://flags/#enable-quic -> Disabled"
echo "3. CMD админ: netsh interface tcp set global timestamps=enabled"
echo "4. Выключи IPv6 на сетевой карте (Свойства адаптера)"
echo "5. Keenetic: ПК только в политике XKeen, ускоритель ВЫКЛ"
echo ""
echo "curl с роутера (/ #) НЕ проверяет XKeen — только ПК."
