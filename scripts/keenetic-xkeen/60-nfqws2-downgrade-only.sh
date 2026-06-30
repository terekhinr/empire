#!/bin/sh
# Откат ТОЛЬКО nfqws2 → 1.1.5 + unified конфиг МТС. Прошивку роутера НЕ трогаем.
# Запуск с роутера (нужен exec sh или ssh :222):
#   curl -fsSL http://193.233.232.48:8787/60-nfqws2-downgrade-only.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
IPK_URL="${NFQWS2_IPK_URL:-$BASE/firmware/nfqws2-keenetic_1.1.5_mipsel-3.4.ipk}"
IPK="/opt/tmp/nfqws2-downgrade.ipk"

echo "========== 1. STOP proxies =========="
/opt/bin/skeen stop 2>/dev/null || true
killall -9 skeen-box xray nfqws2 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true

echo "========== 2. DOWNGRADE nfqws2 → 1.1.5 =========="
mkdir -p /opt/tmp
wget -q -O "$IPK" "$IPK_URL" || curl -fsSL -o "$IPK" "$IPK_URL"
echo "Before:"; opkg list-installed 2>/dev/null | grep nfqws || true
opkg install --force-downgrade --force-reinstall "$IPK"
echo "After:"; opkg list-installed 2>/dev/null | grep nfqws || true
/opt/sbin/nfqws2 --version 2>/dev/null || /opt/bin/nfqws2 --version 2>/dev/null || true

echo "========== 3. unified MTS config =========="
curl -fL -o /opt/etc/nfqws2/nfqws2.conf "$BASE/nfqws2-mts-unified.conf"
ISP="eth3"
for c in eth3 eth2.2 ppp0 eth2; do
  [ -d "/sys/class/net/$c" ] && ISP="$c" && break
done
sed -i "s/^ISP_INTERFACE=.*/ISP_INTERFACE=\"$ISP\"/" /opt/etc/nfqws2/nfqws2.conf

echo "========== 4. policies + start =========="
ndmc -c "ip hotspot host 94:de:80:64:ed:e6 conform" 2>/dev/null || true
ndmc -c "ip hotspot host 04:05:dd:c5:eb:a4 conform" 2>/dev/null || true
ndmc -c "system configuration save" 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 enable 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 start
sleep 4
/opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true

echo "========== 5. QUIC block =========="
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
for u in https://www.youtube.com https://www.google.com/generate_204 https://ya.ru; do
  code=$(curl -4 -o /dev/null -s -w "%{http_code}" --connect-timeout 12 "$u" 2>/dev/null || echo ERR)
  echo "$u -> $code"
done
echo "nfqws2=$(pgrep nfqws2 || echo OFF) nfqueue=$(iptables-save 2>/dev/null | grep -c NFQUEUE || echo 0)"
