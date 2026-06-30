#!/bin/sh
# Салют ТВ: Google по IP (без SNI) + длинный sniff для медленного TLS на Android TV
# curl -fsSL http://193.233.232.48:8787/38-fix-salut-youtube.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
SKEEN_BASE="$BASE/skeen"
WORK=/opt/etc/skeen
CFG=$WORK/config

echo "========== 1. SKeen CONFIG (Salut fix) =========="
curl -fL -o "$CFG/route.json" "$SKEEN_BASE/route.json"
curl -fL -o "$CFG/inbounds.json" "$SKEEN_BASE/inbounds.json"
/opt/bin/skeen-box format -w -C "$CFG" 2>/dev/null || true
/opt/bin/skeen-box check -C "$CFG" 2>/dev/null || true

echo "========== 2. QUIC BLOCK (TCP fallback) =========="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD 1 -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -t mangle -D PREROUTING -i br0 -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -t mangle -I PREROUTING -i br0 -p udp --dport 443 -j DROP 2>/dev/null || true

echo "========== 3. RESTART =========="
rm -f "$WORK/cache.db" 2>/dev/null || true
conntrack -F 2>/dev/null || true
/opt/bin/skeen restart
sleep 5
/opt/bin/skeen status

echo ""
echo "OK. На Салюте: закрой YouTube полностью -> открой снова."
echo "Лог: grep 192.168.1.141 /opt/var/log/sing-box.log | grep vless | tail"
