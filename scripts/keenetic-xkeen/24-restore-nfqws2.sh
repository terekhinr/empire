#!/bin/sh
# ОТКАТ: выключить XKeen, включить nfqws2 (как было когда работало)
# curl -fsSL http://193.233.232.48:8787/24-restore-nfqws2.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

echo "=== 1. Остановка XKeen ==="
xkeen -stop 2>/dev/null || true
killall -9 xray 2>/dev/null || true
sleep 2

echo "=== 2. Снятие костылей iptables ==="
PORT=61219
for ip in 192.168.1.112 192.168.1.141; do
  iptables -t nat -D PREROUTING -s "$ip/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $PORT 2>/dev/null || true
  iptables -t mangle -D PREROUTING -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
  iptables -D FORWARD -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
done
conntrack -F 2>/dev/null || true

echo "=== 3. Blob Google (для googlevideo / ТВ) ==="
mkdir -p /opt/etc/nfqws2/blobs
cd /opt/etc/nfqws2/blobs
[ -s tls_clienthello_www_google_com.bin ] || wget -q -O tls_clienthello_www_google_com.bin \
  "https://raw.githubusercontent.com/bol-van/zapret/master/files/fake/tls_clienthello_www_google_com.bin"
[ -s quic_initial_www_google_com.bin ] || wget -q -O quic_initial_www_google_com.bin \
  "https://raw.githubusercontent.com/bol-van/zapret/master/files/fake/quic_initial_www_google_com.bin"
ls -la tls_clienthello_www_google_com.bin quic_initial_www_google_com.bin

echo "=== 4. Запуск nfqws2 ==="
if [ ! -f /opt/etc/init.d/S51nfqws2 ]; then
  echo "ОШИБКА: nfqws2 не установлен. opkg install nfqws2-keenetic"
  exit 1
fi
/opt/etc/init.d/S51nfqws2 enable 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 start
sleep 3

NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE || echo 0)
echo "NFQUEUE rules: $NFQ"
xkeen -status 2>/dev/null || echo "xkeen stopped"
pgrep nfqws2 || echo "WARN: nfqws2 not running"
echo ""
echo "Keenetic Web:"
echo "  - Destroy_ и Салют -> БЕЗ политики XKeen (обычный интернет)"
echo "  - Сетевой ускоритель ВЫКЛ"
echo "  - DoH Cloudflare 1.1.1.1"
echo ""
echo "Проверка: Chrome youtube.com + SmartTube на Салюте"
