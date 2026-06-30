#!/bin/sh
# БАЗОВАЯ схема: SKeen (sing-box) + Xray VPS — то что у вас работало «более-менее».
# Без XKeen, без nfqws2, без экспериментов с sniff/vision.
# curl -fsSL http://193.233.232.48:8787/46-skeen-baseline.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"

echo "========== 1. VPS xray =========="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' || true
sleep 3

echo "========== 2. nfqws2 OFF =========="
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

echo "========== 3. SKeen baseline config =========="
curl -fL -o /opt/etc/skeen/skeen.json "$SKEEN_BASE/skeen.json"
for f in route.json inbounds.json outbounds.json dns.json log.json experimental.json; do
  curl -fL -o "/opt/etc/skeen/config/$f" "$SKEEN_BASE/$f"
done
curl -fL -o /opt/etc/skeen/watchdog.sh "$SKEEN_BASE/watchdog.sh"
chmod +x /opt/etc/skeen/watchdog.sh
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config 2>/dev/null || true

echo "========== 4. QUIC block =========="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true

echo "========== 5. Transmission 01-06 MSK =========="
curl -fL -o /opt/etc/transmission-schedule.sh "$BASE/transmission-schedule.sh" 2>/dev/null || true
chmod +x /opt/etc/transmission-schedule.sh 2>/dev/null || true
/opt/etc/transmission-schedule.sh stop 2>/dev/null || true

echo "========== 6. cron =========="
TMP=/tmp/cron-base.$$
( crontab -l 2>/dev/null | grep -vE 'skeen/watchdog|transmission-schedule'
  echo "*/5 * * * * /opt/etc/skeen/watchdog.sh"
  echo "0 1 * * * /opt/etc/transmission-schedule.sh start"
  echo "0 6 * * * /opt/etc/transmission-schedule.sh stop"
  echo "*/10 * * * * /opt/etc/transmission-schedule.sh"
) > "$TMP" 2>/dev/null || true
[ -s "$TMP" ] && crontab "$TMP" || true
rm -f "$TMP"

echo "========== 7. clean restart =========="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
: > /opt/var/log/sing-box.log 2>/dev/null || true
/opt/bin/skeen start
sleep 5

echo "========== STATUS =========="
/opt/bin/skeen status
grep '"name"' /opt/etc/skeen/skeen.json
netstat -tn 2>/dev/null | grep ':8443' | grep -c ESTABLISHED || echo 0
echo ""
echo "Keenetic: политика Singbox -> Destroy_ + СберТелек, ускоритель ВЫКЛ"
echo "ПК: Ctrl+Shift+N -> youtube.com"
