#!/bin/sh
# YouTube: сброс зависших туннелей + QUIC block + REDIRECT
# curl -fsSL http://193.233.232.48:8787/22-youtube-fix.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
PC=192.168.1.112
SALUT=192.168.1.141
PORT=61219
DAT=/opt/etc/xray/dat

for f in geosite_v2fly.dat geoip_v2fly.dat geosite_zkeen.dat geoip_zkeenip.dat; do
  ln -sf "$DAT/$f" /opt/sbin/$f 2>/dev/null || true
done

# routing: весь перехваченный -> VPS, QUIC (udp/443) block
cat > /opt/etc/xray/configs/05_routing.json << 'EOF'
{
  "routing": {
    "rules": [
      {
        "inboundTag": ["redirect", "tproxy"],
        "outboundTag": "block",
        "type": "field",
        "network": "udp",
        "port": "135, 137, 138, 139, 443"
      },
      {
        "inboundTag": ["redirect", "tproxy"],
        "outboundTag": "vless-reality",
        "type": "field"
      }
    ]
  }
}
EOF

BEFORE=$(netstat -an 2>/dev/null | grep 8443 | grep ESTABLISHED | wc -l)
killall -9 xray 2>/dev/null || true
sleep 2
xkeen -start 2>&1 || xkeen -restart 2>&1
sleep 4

for ip in $PC $SALUT; do
  iptables -t nat -D PREROUTING -s "$ip/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $PORT 2>/dev/null || true
  iptables -t nat -I PREROUTING 1 -s "$ip/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $PORT
  iptables -t mangle -D PREROUTING -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
  iptables -t mangle -I PREROUTING 1 -s "$ip/32" -p udp --dport 443 -j DROP
done
conntrack -F 2>/dev/null || true

AFTER=$(netstat -an 2>/dev/null | grep 8443 | grep ESTABLISHED | wc -l)
echo "tunnels: $BEFORE -> $AFTER"
xkeen -status
iptables -t nat -L PREROUTING -n -v | grep 61219 | head -2
echo "Chrome: youtube.com -> ролик"
