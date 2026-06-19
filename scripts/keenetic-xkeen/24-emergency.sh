#!/bin/sh
# Аварийный запуск когда xkeen -restart падает
# curl -fsSL http://193.233.232.48:8787/24-emergency.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
SALUT=192.168.1.141
PORT=61219
DAT=/opt/etc/xray/dat

for f in geosite_v2fly.dat geoip_v2fly.dat geosite_zkeen.dat geoip_zkeenip.dat; do
  ln -sf "$DAT/$f" /opt/sbin/$f 2>/dev/null || true
done

killall xray 2>/dev/null || true
sleep 1
/opt/sbin/xray run -confdir /opt/etc/xray/configs >/dev/null 2>&1 &
sleep 3

# Только Салют (ПК = Amnezia)
iptables -t nat -D PREROUTING -s 192.168.1.112/32 ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $PORT 2>/dev/null || true
iptables -t nat -D PREROUTING -s "$SALUT/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $PORT 2>/dev/null || true
iptables -t nat -I PREROUTING 1 -s "$SALUT/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $PORT

pgrep xray >/dev/null && echo "OK: xray + Salut REDIRECT" || echo "FAIL: xray not running"
echo "tunnels: $(netstat -an 2>/dev/null | grep 8443 | grep ESTABLISHED | wc -l)"
