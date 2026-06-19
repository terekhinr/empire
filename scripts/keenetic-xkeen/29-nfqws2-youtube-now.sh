#!/bin/sh
# YouTube fix: QUIC block + restore NFQUEUE + apply config + conntrack flush
# curl -fsSL http://193.233.232.48:8787/29-nfqws2-youtube-now.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

curl -fL -o /opt/etc/nfqws2/nfqws2.conf "$BASE/nfqws2-mts.conf"
curl -fL -o /opt/etc/nfqws2/watchdog.sh "$BASE/28-nfqws2-watchdog.sh"
chmod +x /opt/etc/nfqws2/watchdog.sh
( crontab -l 2>/dev/null | grep -v nfqws2/watchdog; echo "*/1 * * * * /opt/etc/nfqws2/watchdog.sh" ) | crontab -

# ndm hook — фоновое восстановление через 8 сек после rebuild Keenetic
curl -fL -o /opt/etc/ndm/netfilter.d/100-nfqws2.sh "$BASE/100-nfqws2-hook.sh"
chmod +x /opt/etc/ndm/netfilter.d/100-nfqws2.sh
rm -f /opt/etc/ndm/netfilter.d/100-nfqws2.sh.disabled 2>/dev/null || true

# Force TCP for YouTube — FORWARD, не mangle (иначе гонка с ndm hook)
iptables -C FORWARD -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -s 192.168.1.0/24 -p udp --dport 443 -j DROP

: > /opt/etc/nfqws2/lists/auto.list
conntrack -F 2>/dev/null || true

modprobe xt_NFQUEUE 2>/dev/null || true
modprobe nfnetlink_queue 2>/dev/null || true
if pgrep nfqws2 >/dev/null; then
  /opt/etc/init.d/S51nfqws2 reload 2>/dev/null || true
else
  /opt/etc/init.d/S51nfqws2 start 2>/dev/null || true
fi
sleep 2
for i in 1 2 3 4 5 6 7 8 9 10; do
  /opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true
  sleep 2
  NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE || true)
  [ "${NFQ:-0}" -ge 9 ] && break
done
conntrack -F 2>/dev/null || true

NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE || true)
POST=$(iptables -t mangle -L nfqws_post -n -v 2>/dev/null | awk '/NFQUEUE/ {s+=$1} END {print s+0}')
echo "nfqws2: $(pgrep nfqws2 || echo OFF)"
echo "NFQUEUE=$NFQ post_pkts=$POST QUIC_BLOCK=on"
echo "ПК: закрой YouTube, Ctrl+Shift+N, открой ролик."
