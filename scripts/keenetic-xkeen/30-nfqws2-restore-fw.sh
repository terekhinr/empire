#!/bin/sh
# Одноразовое восстановление NFQUEUE без ndm-hook (гонка с Keenetic firewall)
# curl -fsSL http://193.233.232.48:8787/30-nfqws2-restore-fw.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

# ndm hook — фоновое восстановление (см. 100-nfqws2-hook.sh)
curl -fL -o /opt/etc/ndm/netfilter.d/100-nfqws2.sh "$BASE/100-nfqws2-hook.sh"
chmod +x /opt/etc/ndm/netfilter.d/100-nfqws2.sh
rm -f /opt/etc/ndm/netfilter.d/100-nfqws2.sh.disabled 2>/dev/null || true

curl -fL -o /opt/etc/nfqws2/watchdog.sh "$BASE/28-nfqws2-watchdog.sh"
chmod +x /opt/etc/nfqws2/watchdog.sh
( crontab -l 2>/dev/null | grep -v nfqws2/watchdog; echo "*/1 * * * * /opt/etc/nfqws2/watchdog.sh" ) | crontab -

modprobe xt_NFQUEUE 2>/dev/null || true
modprobe nfnetlink_queue 2>/dev/null || true

# НЕ вызывать firewall_stop — Keenetic после него сносит цепочки
i=1
while [ "$i" -le 10 ]; do
  /opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true
  sleep 2
  NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE || true)
  [ "${NFQ:-0}" -ge 9 ] && break
  i=$((i + 1))
done

iptables -C FORWARD -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || true

pgrep nfqws2 >/dev/null || /opt/etc/init.d/S51nfqws2 start 2>/dev/null || true
conntrack -F 2>/dev/null || true

NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE || true)
POST=$(iptables -t mangle -L nfqws_post -n -v 2>/dev/null | awk '/NFQUEUE/ {s+=$1} END {print s+0}')
echo "nfqws2: $(pgrep nfqws2 || echo OFF) NFQUEUE=${NFQ:-0} post_pkts=${POST:-0}"
echo "hook=disabled cron=1min"
