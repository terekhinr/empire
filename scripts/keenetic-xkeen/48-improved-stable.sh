#!/bin/sh
# Улучшенная схема v2: SKeen + dual-port VLESS Reality + urltest failover.
#
# Контекст (Москва, MTS, CGNAT, Keenetic Giga KN-1011 / MIPS):
# - WAN за CGNAT: входящие с интернета нестабильны, исходящие на VPS — ОК
# - MTS может деградировать нестандартные порты → два порта 8443 + 2053 + urltest
# - YouTube = десятки параллельных TCP/443 → xray 26.x зависает → pin 24.12.31
# - QUIC/UDP443 блокируем → видео идёт по TCP через туннель
# - Политика Singbox ТОЛЬКО на Destroy_ + СберТелек; остальной LAN — direct
#
# curl -fsSL http://193.233.232.48:8787/48-improved-stable.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"

echo "========== 0. VPS: stable xray + dual port =========="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' || true
sleep 4

echo "========== 1. nfqws2 OFF =========="
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
killall nfqws2 2>/dev/null || true

echo "========== 2. SKeen improved config =========="
curl -fL -o /opt/etc/skeen/skeen.json "$SKEEN_BASE/skeen.json"
for f in route.json inbounds.json outbounds.json dns.json log.json experimental.json; do
  curl -fL -o "/opt/etc/skeen/config/$f" "$SKEEN_BASE/$f"
done
curl -fL -o /opt/etc/skeen/watchdog.sh "$SKEEN_BASE/watchdog.sh"
chmod +x /opt/etc/skeen/watchdog.sh
/opt/bin/skeen-box check -D /opt/etc/skeen -C /opt/etc/skeen/config
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config 2>/dev/null || true

echo "========== 3. QUIC block (FORWARD udp/443) =========="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true

echo "========== 4. Transmission 01-06 MSK =========="
curl -fL -o /opt/etc/transmission-schedule.sh "$BASE/transmission-schedule.sh" 2>/dev/null || true
chmod +x /opt/etc/transmission-schedule.sh 2>/dev/null || true
/opt/etc/transmission-schedule.sh stop 2>/dev/null || true

echo "========== 5. cron =========="
TMP=/tmp/cron-improved.$$
( crontab -l 2>/dev/null | grep -vE 'skeen/watchdog|47-proactive-sync|transmission-schedule'
  echo "*/2 * * * * /opt/etc/skeen/watchdog.sh"
  echo "20 * * * * curl -fsSL $BASE/47-proactive-sync.sh | sh"
  echo "0 1 * * * /opt/etc/transmission-schedule.sh start"
  echo "0 6 * * * /opt/etc/transmission-schedule.sh stop"
  echo "*/10 * * * * /opt/etc/transmission-schedule.sh"
) > "$TMP" 2>/dev/null || true
[ -s "$TMP" ] && crontab "$TMP" || true
rm -f "$TMP"

echo "========== 6. clean restart =========="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2
conntrack -D -p tcp --dst 193.233.232.48 2>/dev/null || true
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
: > /opt/var/log/sing-box.log 2>/dev/null || true
/opt/bin/skeen start
sleep 8

echo "========== STATUS =========="
/opt/bin/skeen status
grep '"name"' /opt/etc/skeen/skeen.json
echo "VPS tunnels:" \
  $(netstat -tn 2>/dev/null | grep '193.233.232.48' | grep -c ESTABLISHED || echo 0) \
  "established"
echo ""
echo "Keenetic Web: политика Singbox -> Destroy_ + СберТелек, ускоритель ВЫКЛ, DoH ВКЛ"
echo "Zashboard: http://192.168.1.1:9999/ui/"
echo "ПК: Ctrl+Shift+N -> youtube.com"
