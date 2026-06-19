#!/bin/sh
# YouTube fix: обновить конфиг + блок QUIC (UDP/443) для Chrome/SmartTube.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_SKEEN_BASE:-http://193.233.232.48:8787/skeen}"
WORK=/opt/etc/skeen
CFG=$WORK/config

echo "=== CONFIG ==="
curl -fL -o "$WORK/skeen.json" "$BASE/skeen.json"
for f in dns.json route.json; do
  curl -fL -o "$CFG/$f" "$BASE/$f"
done
/opt/bin/skeen-box format -w -C "$CFG"

echo "=== QUIC BLOCK (force TCP for YouTube) ==="
# Удалить старые правила если есть
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -D FORWARD -p udp --dport 443 -m string --algo bm --string "google" -j DROP 2>/dev/null || true
# Блок UDP/443 на LAN — Chrome/SmartTube перейдут на TCP
iptables -I FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true

echo "=== RESTART ==="
/opt/bin/skeen restart
sleep 3
/opt/bin/skeen status

echo ""
echo "OK. Проверь YouTube в Chrome (Ctrl+Shift+N)."
