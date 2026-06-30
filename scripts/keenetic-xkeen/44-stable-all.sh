#!/bin/sh
# Стабильная схема «всё сразу»:
# - Singbox политика: только ПК + Салют, только TCP/443
# - Google/YouTube -> VPS, остальное -> direct (DNS через роутер, без hijack)
# - Transmission: 01:00-06:00 MSK (днём не мешает)
# - Watchdog: рестарт только если sing-box упал
# curl -fsSL http://193.233.232.48:8787/44-stable-all.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"

echo "========== 1. VPS xray =========="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' || true
sleep 3

echo "========== 2. Transmission schedule =========="
curl -fL -o /opt/etc/transmission-schedule.sh "$BASE/transmission-schedule.sh" 2>/dev/null || true
chmod +x /opt/etc/transmission-schedule.sh 2>/dev/null || true
/opt/etc/transmission-schedule.sh stop 2>/dev/null || true
TMP=/tmp/cron-all.$$
( crontab -l 2>/dev/null | grep -v transmission-schedule
  echo "0 1 * * * /opt/etc/transmission-schedule.sh start"
  echo "0 6 * * * /opt/etc/transmission-schedule.sh stop"
  echo "*/10 * * * * /opt/etc/transmission-schedule.sh"
) > "$TMP" 2>/dev/null || true
[ -s "$TMP" ] && crontab "$TMP" || true
rm -f "$TMP"

echo "========== 3. SKeen configs =========="
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

echo "========== 5. WATCHDOG cron =========="
TMP2=/tmp/cron-wd.$$
( crontab -l 2>/dev/null | grep -v skeen/watchdog; echo "*/3 * * * * /opt/etc/skeen/watchdog.sh" ) > "$TMP2" 2>/dev/null || echo "*/3 * * * * /opt/etc/skeen/watchdog.sh" > "$TMP2"
crontab "$TMP2"
rm -f "$TMP2"

echo "========== 6. RESTART =========="
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
: > /opt/var/log/sing-box.log 2>/dev/null || true
/opt/bin/skeen restart
sleep 6

echo "========== 7. STATUS =========="
/opt/bin/skeen status
grep '"name"' /opt/etc/skeen/skeen.json
pidof transmissiond >/dev/null && echo "WARN: transmission running (daytime)" || echo "OK: transmission stopped (daytime)"
netstat -tn 2>/dev/null | grep ':8443' | grep -c ESTABLISHED || echo 0
echo "OK: Singbox=PC+Salut, YouTube->VPS, torrents 01-06 MSK"
