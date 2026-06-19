#!/bin/sh
# Вернуть nfqws2 (работало раньше). SKeen/sing-box полностью выключаем.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

echo "=== 1. STOP SKeen ==="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
rm -f /opt/etc/ndm/netfilter.d/skeen_firewall.sh 2>/dev/null || true
rm -f /opt/etc/init.d/S99SKeen 2>/dev/null || true

echo "=== 2. Снять QUIC-block и мусор iptables ==="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -t mangle -D PREROUTING -i br0 -p udp --dport 443 -j DROP 2>/dev/null || true
for ip in 192.168.1.112 192.168.1.141; do
  iptables -t mangle -D PREROUTING -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
  iptables -D FORWARD -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
done
conntrack -F 2>/dev/null || true

echo "=== 3. Blob Google ==="
mkdir -p /opt/etc/nfqws2/blobs
cd /opt/etc/nfqws2/blobs
[ -s tls_clienthello_www_google_com.bin ] || wget -q -O tls_clienthello_www_google_com.bin \
  "https://raw.githubusercontent.com/bol-van/zapret/master/files/fake/tls_clienthello_www_google_com.bin"
[ -s quic_initial_www_google_com.bin ] || wget -q -O quic_initial_www_google_com.bin \
  "https://raw.githubusercontent.com/bol-van/zapret/master/files/fake/quic_initial_www_google_com.bin"

echo "=== 4. nfqws2 ==="
if [ ! -f /opt/etc/init.d/S51nfqws2 ]; then
  echo "ОШИБКА: nfqws2 не установлен"
  exit 1
fi
/opt/etc/init.d/S51nfqws2 enable 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 start
sleep 3
iptables-save 2>/dev/null | grep -c NFQUEUE | xargs echo "NFQUEUE rules:"
pgrep nfqws2 || echo "WARN: nfqws2 not running"

echo ""
echo "=== DONE ==="
echo "Keenetic: Destroy_ и Салют БЕЗ политики XKeen/SKeen"
echo "Ускоритель ВЫКЛ, DoH Cloudflare"
echo "YouTube: Ctrl+Shift+N"
