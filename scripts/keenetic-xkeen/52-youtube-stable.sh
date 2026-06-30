#!/bin/sh
# Стабильный YouTube: SKeen + xray :8443, FIN_WAIT guard, синхронный recovery.
# curl -fsSL http://193.233.232.48:8787/52-youtube-stable.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="http://193.233.232.48:8787"
SKEEN="$BASE/skeen"

curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' || true
sleep 4

/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

for f in skeen.json route.json inbounds.json outbounds.json dns.json log.json experimental.json; do
  if [ "$f" = "skeen.json" ]; then
    curl -fL -o /opt/etc/skeen/skeen.json "$SKEEN/skeen.json"
  else
    curl -fL -o "/opt/etc/skeen/config/$f" "$SKEEN/$f"
  fi
done
curl -fL -o /opt/etc/skeen/watchdog.sh "$SKEEN/watchdog.sh"
chmod +x /opt/etc/skeen/watchdog.sh
/opt/bin/skeen-box check -D /opt/etc/skeen -C /opt/etc/skeen/config
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config 2>/dev/null || true

iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true

/opt/etc/transmission-schedule.sh stop 2>/dev/null || true

TMP=/tmp/cron52.$$
( crontab -l 2>/dev/null | grep -vE 'skeen/watchdog|skeen/tunnel-refresh|47-proactive|49-|50-|51-|52-'
  echo "*/3 * * * * /opt/etc/skeen/watchdog.sh"
) > "$TMP" 2>/dev/null || true
[ -s "$TMP" ] && crontab "$TMP" || true
rm -f "$TMP"

/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2
conntrack -D -p tcp --dst 193.233.232.48 2>/dev/null || true
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
: > /opt/var/log/sing-box.log 2>/dev/null || true
/opt/bin/skeen start
sleep 12

err=$(grep -c ERROR /opt/var/log/sing-box.log 2>/dev/null || echo 0)
yt=$(grep -ci youtube /opt/var/log/sing-box.log 2>/dev/null || echo 0)
ok=$(grep -c 'outbound/vless\[vless-vps\]: outbound connection to www.youtube.com' /opt/var/log/sing-box.log 2>/dev/null || echo 0)
echo "errors=$err youtube_hits=$yt youtube_ok=$ok"
grep -iE 'youtube|googlevideo|ytimg' /opt/var/log/sing-box.log 2>/dev/null | tail -8 || true
/opt/bin/skeen status | head -3
