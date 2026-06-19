#!/bin/sh
# YouTube крутит спиннер: блок QUIC (UDP/443) → Chrome качает видео по TCP через VPS.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

echo "=== QUIC OFF (UDP/443) ==="
# FORWARD — для устройств за роутером
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
# PREROUTING — на всякий случай с LAN
iptables -t mangle -D PREROUTING -i br0 -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -t mangle -I PREROUTING -i br0 -p udp --dport 443 -j DROP 2>/dev/null || true

echo "=== FLUSH STALE VPS TUNNELS ==="
conntrack -D -p tcp --dport 8443 2>/dev/null || true
conntrack -D -p udp --dport 443 2>/dev/null || true

echo "=== RESTART SKeen ==="
/opt/bin/skeen restart
sleep 5
/opt/bin/skeen status

echo ""
echo "OK:"
echo "  1. Закрой все вкладки YouTube"
echo "  2. Ctrl+Shift+N → youtube.com"
echo "  3. Amnezia ВЫКЛ"
echo "  4. Если всё ещё спиннер — chrome://net-internals/#sockets → Flush socket pools"
