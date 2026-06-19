#!/bin/sh
# Оптимизация YouTube: VPS xray tuning + свежий SKeen config + полный сброс туннелей
# curl -fsSL http://193.233.232.48:8787/37-optimize-youtube-vps.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"
VPS_PORT="${VPS_PROXY_PORT:-8443}"

echo "========== 0. VPS xray restart =========="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' 2>/dev/null || true
sleep 3

echo "========== 1. STOP nfqws2 =========="
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

echo "========== 2. SKeen CONFIG =========="
WORK=/opt/etc/skeen
CFG=$WORK/config
curl -fL -o "$WORK/skeen.json" "$SKEEN_BASE/skeen.json"
for f in inbounds.json outbounds.json route.json dns.json log.json experimental.json; do
  curl -fL -o "$CFG/$f" "$SKEEN_BASE/$f"
done
/opt/bin/skeen-box format -w -C "$CFG" 2>/dev/null || true

echo "========== 3. QUIC BLOCK =========="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true

echo "========== 4. WATCHDOG =========="
curl -fL -o /opt/etc/skeen/watchdog.sh "$SKEEN_BASE/watchdog.sh"
chmod +x /opt/etc/skeen/watchdog.sh
TMP=/tmp/skeen-crontab.$$
( crontab -l 2>/dev/null | grep -v skeen/watchdog; echo "*/2 * * * * /opt/etc/skeen/watchdog.sh" ) > "$TMP" 2>/dev/null || echo "*/2 * * * * /opt/etc/skeen/watchdog.sh" > "$TMP"
crontab "$TMP"
rm -f "$TMP"

echo "========== 5. CLEAN RESTART =========="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2
conntrack -F 2>/dev/null || true
conntrack -D -p tcp --dport "$VPS_PORT" 2>/dev/null || true
: > /opt/var/log/sing-box.log 2>/dev/null || true
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
/opt/bin/skeen start
sleep 5
conntrack -F 2>/dev/null || true

echo "========== 6. STATUS =========="
/opt/bin/skeen status 2>/dev/null || true
T=$(netstat -tn 2>/dev/null | grep ":$VPS_PORT" | wc -l)
FIN=$(netstat -tn 2>/dev/null | grep ":$VPS_PORT" | grep -c FIN_WAIT || true)
echo "VPS tunnels=$T FIN_WAIT=$FIN port=$VPS_PORT"
echo "ПК: ipconfig /flushdns, Ctrl+Shift+N -> youtube.com"
