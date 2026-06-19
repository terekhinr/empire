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
n=$(netstat -tn 2>/dev/null | grep ':8443' | wc -l)
if [ "$n" -gt 40 ] || ! pidof skeen-box >/dev/null 2>&1; then
  conntrack -D -p tcp --dport 8443 2>/dev/null || true
  /opt/bin/skeen restart
fi
WEOF
chmod +x "$WD"
( crontab -l 2>/dev/null | grep -v skeen/watchdog; echo "*/10 * * * * $WD" ) | crontab -

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
