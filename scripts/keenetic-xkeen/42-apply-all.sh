#!/bin/sh
# Полная настройка через SSH: Singbox policy match + configs + pause torrents
# curl -fsSL http://193.233.232.48:8787/42-apply-all.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"

echo "========== 1. VPS xray =========="
curl -fsS -X POST "$BASE/restart-xray" -H 'Content-Type: application/json' -d '{}' || true
sleep 3

echo "========== 2. PAUSE Transmission (CPU) =========="
if pidof transmission-daemon >/dev/null 2>&1 || pidof transmissiond >/dev/null 2>&1; then
  killall transmission-daemon 2>/dev/null || true
  killall transmissiond 2>/dev/null || true
  echo "Transmission stopped"
else
  echo "Transmission not running"
fi

echo "========== 3. SKeen CONFIG (policy=Singbox) =========="
curl -fL -o /opt/etc/skeen/skeen.json "$SKEEN_BASE/skeen.json"
for f in route.json inbounds.json outbounds.json dns.json log.json experimental.json; do
  curl -fL -o "/opt/etc/skeen/config/$f" "$SKEEN_BASE/$f"
done
/opt/bin/skeen-box format -w -C /opt/etc/skeen/config 2>/dev/null || true

echo "========== 4. QUIC BLOCK =========="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true

echo "========== 5. RESTART SKeen =========="
rm -f /opt/etc/skeen/cache.db 2>/dev/null || true
: > /opt/var/log/sing-box.log 2>/dev/null || true
/opt/bin/skeen restart
sleep 6

echo "========== 6. STATUS =========="
/opt/bin/skeen status
grep '"name"' /opt/etc/skeen/skeen.json
T=$(netstat -tn 2>/dev/null | grep ':8443' | wc -l)
echo "VPS tunnels=$T"
echo "OK: policy Singbox -> Destroy_ + СберТелек"
