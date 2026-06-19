#!/bin/sh
# Стабильный YouTube: TCP-only redirect, без multiplex, policy SKeen, блок QUIC.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_SKEEN_BASE:-http://193.233.232.48:8787/skeen}"
WORK=/opt/etc/skeen
CFG=$WORK/config

echo "=== CONFIG ==="
curl -fL -o "$WORK/skeen.json" "$BASE/skeen.json"
for f in inbounds.json outbounds.json route.json dns.json; do
  curl -fL -o "$CFG/$f" "$BASE/$f"
done
/opt/bin/skeen-box format -w -C "$CFG"

echo "=== KILL STALE TUNNELS ==="
netstat -tn 2>/dev/null | grep ':8443' | wc -l | xargs echo "tunnels before:"
conntrack -D -p tcp --dport 8443 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2

echo "=== QUIC BLOCK (UDP/443 LAN) ==="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true

echo "=== WATCHDOG CRON ==="
WD=/opt/etc/skeen/watchdog.sh
cat > "$WD" << 'WEOF'
#!/bin/sh
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
n=$(netstat -tn 2>/dev/null | grep ':8443' | wc -l)
fin=$(netstat -tn 2>/dev/null | grep ':8443' | grep -c FIN_WAIT || true)
est=$(netstat -tn 2>/dev/null | grep ':8443' | grep -c ESTABLISHED || true)
deadlines=$(grep -c 'context deadline exceeded' /opt/var/log/sing-box.log 2>/dev/null || echo 0)
need=0
if ! pidof skeen-box >/dev/null 2>&1; then need=1; fi
if [ "$n" -gt 20 ]; then need=1; fi
if [ "$fin" -gt 10 ]; then need=1; fi
if [ "$deadlines" -gt 10 ] 2>/dev/null; then need=1; fi
if [ "$fin" -gt 5 ] && [ "$est" -lt 3 ]; then need=1; fi
if [ "$need" -eq 1 ]; then
  curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' 2>/dev/null || true
  sleep 2
  conntrack -F 2>/dev/null || true
  conntrack -D -p tcp --dport 8443 2>/dev/null || true
  : > /opt/var/log/sing-box.log 2>/dev/null || true
  rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
  /opt/bin/skeen restart
fi
WEOF
chmod +x "$WD"
TMP=/tmp/skeen-crontab.$$
( crontab -l 2>/dev/null | grep -v skeen/watchdog; echo "*/5 * * * * $WD" ) > "$TMP" 2>/dev/null || echo "*/5 * * * * $WD" > "$TMP"
crontab "$TMP"
rm -f "$TMP"

echo "=== RESTART ==="
/opt/bin/skeen restart
sleep 4
netstat -tn 2>/dev/null | grep ':8443' | wc -l | xargs echo "tunnels after:"
/opt/bin/skeen status

echo ""
echo "=== ВАЖНО в Keenetic Web ==="
echo "1. Создай политику «SKeen» (если нет)"
echo "2. В SKeen: только Destroy_ + СберТелек"
echo "3. Удали политику XKeen"
echo "4. Сетевой ускоритель — ВЫКЛ"
echo "5. YouTube: Ctrl+Shift+N, Amnezia выкл"
