#!/bin/sh
# Откат nfqws2-keenetic 1.1.5 + unified конфиг МТС.
# curl -fsSL http://193.233.232.48:8787/56-downgrade-nfqws2-heal.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
IPK="$BASE/nfqws2-keenetic_1.1.5_mipsel-3.4.ipk"

echo "========== 1. STOP proxies =========="
/opt/bin/skeen stop 2>/dev/null || true
killall -9 skeen-box xray 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

echo "========== 2. Policies default =========="
ndmc -c "ip hotspot host 94:de:80:64:ed:e6 conform" 2>/dev/null || true
ndmc -c "ip hotspot host 04:05:dd:c5:eb:a4 conform" 2>/dev/null || true
ndmc -c "system configuration save" 2>/dev/null || true

echo "========== 3. Downgrade nfqws2 1.1.5 =========="
mkdir -p /opt/tmp
curl -fL -o /opt/tmp/nfqws2-downgrade.ipk "$IPK"
opkg install --force-downgrade --force-reinstall /opt/tmp/nfqws2-downgrade.ipk

echo "========== 4. unified MTS config =========="
curl -fL -o /opt/etc/nfqws2/nfqws2.conf "$BASE/nfqws2-mts-unified.conf"
ISP="eth3"
for c in eth3 eth2.2 ppp0 eth2; do
  [ -d "/sys/class/net/$c" ] && ISP="$c" && break
done
sed -i "s/^ISP_INTERFACE=.*/ISP_INTERFACE=\"$ISP\"/" /opt/etc/nfqws2/nfqws2.conf

echo "========== 5. start + quic + watchdog =========="
/opt/etc/init.d/S51nfqws2 enable 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 start
sleep 4
/opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true
iptables -C FORWARD -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -p udp --dport 443 -j DROP
for ip in 192.168.1.112 192.168.1.141; do
  iptables -t mangle -C PREROUTING -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || \
    iptables -t mangle -I PREROUTING 1 -s "$ip/32" -p udp --dport 443 -j DROP
done
curl -fL -o /opt/etc/nfqws2/watchdog.sh "$BASE/28-nfqws2-watchdog.sh"
chmod +x /opt/etc/nfqws2/watchdog.sh
( crontab -l 2>/dev/null | grep -vE "skeen|xkeen|nfqws2/watchdog"; echo "*/1 * * * * /opt/etc/nfqws2/watchdog.sh" ) | crontab -
conntrack -F 2>/dev/null || true

echo "========== 6. VERIFY =========="
/opt/sbin/nfqws2 --version 2>/dev/null || nfqws2 --version 2>/dev/null || true
pgrep nfqws2 || echo "FAIL nfqws2"
echo "NFQUEUE=$(iptables-save 2>/dev/null | grep -c NFQUEUE)"
for u in https://www.google.com/generate_204 https://www.youtube.com https://ya.ru; do
  code=$(curl -4 -o /dev/null -s -w "%{http_code}" --connect-timeout 15 --max-time 20 "$u" 2>/dev/null || echo ERR)
  echo "$u -> $code"
done
echo "skeen=$(pgrep skeen-box || echo OFF)"
echo "========== DONE =========="
