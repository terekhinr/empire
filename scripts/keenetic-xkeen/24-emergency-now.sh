#!/bin/sh
# Экстренное восстановление: geodata + google routing + сброс туннелей + только Салют
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
SALUT=192.168.1.141
PORT=61219
DAT=/opt/etc/xray/dat

for f in geosite_v2fly.dat geoip_v2fly.dat geosite_zkeen.dat geoip_zkeenip.dat; do
  ln -sf "$DAT/$f" /opt/sbin/$f 2>/dev/null || true
done

killall -9 xray 2>/dev/null || true
sleep 2
xkeen -start 2>/dev/null || xkeen -restart 2>/dev/null
sleep 4

# ПК не трогаем — Amnezia на ПК. Только Салют.
iptables -t nat -D PREROUTING -s 192.168.1.112/32 ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $PORT 2>/dev/null || true
iptables -t nat -D PREROUTING -s "$SALUT/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $PORT 2>/dev/null || true
iptables -t nat -I PREROUTING 1 -s "$SALUT/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $PORT
iptables -t mangle -D PREROUTING -s "$SALUT/32" -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -t mangle -I PREROUTING 1 -s "$SALUT/32" -p udp --dport 443 -j DROP 2>/dev/null || true
conntrack -F 2>/dev/null || true

echo "xray: $(pgrep xray || echo DEAD)"
echo "tunnels: $(netstat -an 2>/dev/null | grep 8443 | grep ESTABLISHED | wc -l)"
xkeen -status 2>&1 | tail -1
