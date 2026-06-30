#!/bin/sh
# Минимальный сброс: только nfqws2, без SKeen, без политик.
# ssh root@192.168.1.1 -p 222  ->  curl -fsSL http://193.233.232.48:8787/55-minimal-nfqws2.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="http://193.233.232.48:8787"

killall -9 skeen-box xray nfqws2 2>/dev/null || true
/opt/bin/skeen stop 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true

ndmc -c "ip hotspot host 94:de:80:64:ed:e6 conform" 2>/dev/null || true
ndmc -c "ip hotspot host 04:05:dd:c5:eb:a4 conform" 2>/dev/null || true
ndmc -c "system configuration save" 2>/dev/null || true

conntrack -F 2>/dev/null || true

curl -fL -o /opt/etc/nfqws2/nfqws2.conf "$BASE/nfqws2-mts-unified.conf"
ISP="eth3"
for c in eth3 eth2.2 ppp0 eth2; do
  [ -d "/sys/class/net/$c" ] && ISP="$c" && break
done
sed -i "s/^ISP_INTERFACE=.*/ISP_INTERFACE=\"$ISP\"/" /opt/etc/nfqws2/nfqws2.conf

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

crontab -l 2>/dev/null | grep -vE "skeen|xkeen|47-proactive|tunnel-refresh" | crontab - 2>/dev/null || true
curl -fL -o /opt/etc/nfqws2/watchdog.sh "$BASE/28-nfqws2-watchdog.sh"
chmod +x /opt/etc/nfqws2/watchdog.sh
( crontab -l 2>/dev/null | grep -v nfqws2/watchdog; echo "*/1 * * * * /opt/etc/nfqws2/watchdog.sh" ) | crontab -

if [ -x /opt/etc/keenetic-tunnel/start.sh ]; then
  /opt/etc/keenetic-tunnel/start.sh 2>/dev/null || true
else
  curl -fsSL "$BASE/19-router-access.sh" | sh 2>/dev/null || true
fi

echo "--- RESULT ---"
pgrep nfqws2 || echo "FAIL: nfqws2 not running"
iptables-save 2>/dev/null | grep -c NFQUEUE | xargs echo "NFQUEUE="
curl -4 -o /dev/null -s -w "youtube=%{http_code}\n" --connect-timeout 15 https://www.youtube.com || echo youtube=ERR
curl -4 -o /dev/null -s -w "google=%{http_code}\n" --connect-timeout 10 https://www.google.com/generate_204 || echo google=ERR
curl -4 -o /dev/null -s -w "yandex=%{http_code}\n" --connect-timeout 10 https://ya.ru || echo yandex=ERR
