#!/bin/sh
# Финал: только nfqws2 unified, без SKeen/XKeen. QUIC block + watchdog + tunnel.
# curl -fsSL http://193.233.232.48:8787/53-nfqws2-finalize.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

echo "========== 1. STOP SKeen / XKeen =========="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box xray 2>/dev/null || true
/opt/etc/init.d/S05xkeen stop 2>/dev/null || true
rm -f /opt/etc/init.d/S99SKeen /opt/etc/init.d/S05xkeen 2>/dev/null || true
rm -f /opt/etc/ndm/netfilter.d/skeen_firewall.sh 2>/dev/null || true

echo "========== 2. CRON cleanup =========="
TMP=/tmp/cron53.$$
( crontab -l 2>/dev/null | grep -vE 'skeen|xkeen|47-proactive|49-|50-|51-|52-|tunnel-refresh' || true
  echo "*/1 * * * * /opt/etc/nfqws2/watchdog.sh"
) > "$TMP" 2>/dev/null || echo "*/1 * * * * /opt/etc/nfqws2/watchdog.sh" > "$TMP"
crontab "$TMP"
rm -f "$TMP"

echo "========== 3. nfqws2 unified =========="
curl -fsSL "$BASE/32-nfqws2-unified-youtube.sh" | sh

echo "========== 4. watchdog =========="
curl -fL -o /opt/etc/nfqws2/watchdog.sh "$BASE/28-nfqws2-watchdog.sh"
chmod +x /opt/etc/nfqws2/watchdog.sh
/opt/etc/nfqws2/watchdog.sh || true

echo "========== 5. QUIC block (persistent) =========="
cat > /opt/etc/ndm/netfilter.d/001-nfqws2-quic.sh << 'QUICEOF'
#!/bin/sh
[ "$table" = "filter" ] && {
  iptables -C FORWARD -p udp --dport 443 -j DROP 2>/dev/null || \
    iptables -I FORWARD 1 -p udp --dport 443 -j DROP
  for ip in 192.168.1.112 192.168.1.141; do
    iptables -C FORWARD -s $ip/32 -p udp --dport 443 -j DROP 2>/dev/null || \
      iptables -I FORWARD 1 -s $ip/32 -p udp --dport 443 -j DROP
  done
}
[ "$table" = "mangle" ] && {
  for ip in 192.168.1.112 192.168.1.141; do
    iptables -C PREROUTING -s $ip/32 -p udp --dport 443 -j DROP 2>/dev/null || \
      iptables -I PREROUTING 1 -s $ip/32 -p udp --dport 443 -j DROP
  done
}
exit 0
QUICEOF
chmod +x /opt/etc/ndm/netfilter.d/001-nfqws2-quic.sh
curl -fL -o /opt/etc/ndm/netfilter.d/100-nfqws2-hook.sh "$BASE/100-nfqws2-hook.sh" 2>/dev/null || true
chmod +x /opt/etc/ndm/netfilter.d/100-nfqws2-hook.sh 2>/dev/null || true
for ip in 192.168.1.112 192.168.1.141; do
  iptables -t mangle -C PREROUTING -s $ip/32 -p udp --dport 443 -j DROP 2>/dev/null || \
    iptables -t mangle -I PREROUTING 1 -s $ip/32 -p udp --dport 443 -j DROP
done
iptables -C FORWARD -p udp --dport 443 -j DROP 2>/dev/null || \
  iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true
conntrack -F 2>/dev/null || true

echo "========== 6. reverse tunnel (background, 15s max) =========="
(
  if [ -x /opt/etc/keenetic-tunnel/start.sh ]; then
    /opt/etc/keenetic-tunnel/start.sh
  else
    curl -fsSL "$BASE/19-router-access.sh" | sh
  fi
) >/tmp/keenetic-tunnel.log 2>&1 &
TUN_PID=$!
sleep 15
kill "$TUN_PID" 2>/dev/null || true
wait "$TUN_PID" 2>/dev/null || true
pgrep -fa "ssh.*6222" || echo "tunnel: check /tmp/keenetic-tunnel.log"

echo "========== 7. VERIFY =========="
sleep 3
for u in https://www.youtube.com https://www.google.com/generate_204 https://ya.ru; do
  code=$(curl -4 -o /dev/null -s -w "%{http_code}" --connect-timeout 12 --max-time 20 "$u" 2>/dev/null || echo ERR)
  echo "curl $u -> $code"
done
echo "nfqws2=$(pgrep nfqws2 || echo OFF)"
echo "skeen=$(pgrep skeen-box || echo OFF)"
echo "xray=$(pgrep xray || echo OFF)"
echo "nfqueue=$(iptables-save 2>/dev/null | grep -c NFQUEUE || echo 0)"
echo "quic_drop=$(iptables-save 2>/dev/null | grep 'udp dpt:443' | grep -c DROP || echo 0)"
echo "========== DONE =========="
echo "Keenetic Web: политика SKeen/XKeen — отключить; сетевой ускоритель — ВЫКЛ"
