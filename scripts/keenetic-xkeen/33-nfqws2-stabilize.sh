#!/bin/sh
# Стабилизация: убрать restart из cron, unified config, NFQUEUE, QUIC
# curl -fsSL http://193.233.232.48:8787/33-nfqws2-stabilize.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

# bind-policy БЕЗ restart (restart каждые 30 мин ломал NFQUEUE)
cat > /opt/etc/nfqws2/bind-policy.sh << 'EOF'
#!/bin/sh
export PATH="/opt/bin:/opt/sbin:$PATH"
sleep 45
modprobe xt_NFQUEUE nfnetlink_queue 2>/dev/null || true
/opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true
pgrep nfqws2 >/dev/null || /opt/etc/init.d/S51nfqws2 start 2>/dev/null || true
conntrack -F 2>/dev/null || true
EOF
chmod +x /opt/etc/nfqws2/bind-policy.sh

curl -fL -o /opt/etc/nfqws2/nfqws2.conf "$BASE/nfqws2-mts-unified.conf"
curl -fL -o /opt/etc/nfqws2/watchdog.sh "$BASE/28-nfqws2-watchdog.sh"
curl -fL -o /opt/etc/ndm/netfilter.d/100-nfqws2.sh "$BASE/100-nfqws2-hook.sh"
chmod +x /opt/etc/nfqws2/watchdog.sh /opt/etc/ndm/netfilter.d/100-nfqws2.sh

TMP=/tmp/nfqws-crontab.$$
printf '%s\n' "@reboot /opt/etc/nfqws2/bind-policy.sh" "*/1 * * * * /opt/etc/nfqws2/watchdog.sh" > "$TMP"
crontab "$TMP"
rm -f "$TMP"

kill -TERM "$(pgrep nfqws2)" 2>/dev/null || true
sleep 2
rm -f /opt/var/run/nfqws2.pid
/opt/etc/init.d/S51nfqws2 start 2>/dev/null || true
sleep 2
for i in 1 2 3 4 5 6 7 8; do
  /opt/etc/init.d/S51nfqws2 firewall_iptables 2>/dev/null || true
  sleep 1
  NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE || true)
  [ "${NFQ:-0}" -ge 9 ] && break
done

iptables -C FORWARD -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -s 192.168.1.0/24 -p udp --dport 443 -j DROP 2>/dev/null || true
ip6tables -C FORWARD -p udp --dport 443 -j DROP 2>/dev/null || \
  ip6tables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true
conntrack -F 2>/dev/null || true

POST=$(iptables -t mangle -L nfqws_post -n -v 2>/dev/null | awk '/NFQUEUE/ {s+=$1} END {print s+0}')
echo "nfqws2=$(pgrep nfqws2 || echo OFF) NFQ=$(iptables-save 2>/dev/null | grep -c NFQUEUE) post_pkts=${POST:-0}"
echo "cron=fixed (no restart every 30m)"
echo "ПК: netsh interface tcp set global timestamps=enabled + Ctrl+Shift+N"
