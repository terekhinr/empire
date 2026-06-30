#!/bin/sh
# ФИНАЛЬНЫЙ фикс YouTube: dual xray + selector + полный маршрут Google.
# curl -fsSL http://193.233.232.48:8787/49-youtube-night-fix.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"

echo "========== 1. VPS dual xray =========="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' || true
sleep 5

echo "========== 2. nfqws2 OFF =========="
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

echo "========== 3. SKeen config =========="
curl -fL -o /opt/etc/skeen/skeen.json "$SKEEN_BASE/skeen.json"
for f in route.json inbounds.json outbounds.json dns.json log.json experimental.json; do
  curl -fL -o "/opt/etc/skeen/config/$f" "$SKEEN_BASE/$f"
done
curl -fL -o /opt/etc/skeen/watchdog.sh "$SKEEN_BASE/watchdog.sh"
chmod +x /opt/etc/skeen/watchdog.sh
echo 2053 >/opt/etc/skeen/active-vps-port
/opt/bin/skeen-box check -D /opt/etc/skeen -C /opt/etc/skeen/config
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config 2>/dev/null || true

echo "========== 4. QUIC block =========="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true

echo "========== 5. Transmission off =========="
/opt/etc/transmission-schedule.sh stop 2>/dev/null || true

echo "========== 6. cron =========="
TMP=/tmp/cron-fix.$$
( crontab -l 2>/dev/null | grep -vE 'skeen/watchdog|47-proactive|49-youtube'
  echo "*/1 * * * * /opt/etc/skeen/watchdog.sh"
  echo "25 * * * * curl -fsSL $BASE/47-proactive-sync.sh | sh"
) > "$TMP" 2>/dev/null || true
[ -s "$TMP" ] && crontab "$TMP" || true
rm -f "$TMP"

echo "========== 7. restart =========="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2
conntrack -D -p tcp --dst 193.233.232.48 2>/dev/null || true
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
: > /opt/var/log/sing-box.log 2>/dev/null || true
/opt/bin/skeen start
sleep 10

echo "========== STATUS =========="
/opt/bin/skeen status
grep '"name"' /opt/etc/skeen/skeen.json
echo "errors:" $(grep -c ERROR /opt/var/log/sing-box.log 2>/dev/null || echo 0)
grep -E 'youtube|googlevideo' /opt/var/log/sing-box.log 2>/dev/null | tail -3 || true
echo ""
echo "ПК/Salut: Ctrl+Shift+N -> youtube.com"
