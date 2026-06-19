#!/bin/sh
# ПК + Салют: принудительный перехват TCP -> xray, весь Google через VPS
# curl -fsSL http://193.233.232.48:8787/18-fix-chain.sh | sh
# curl -fsSL http://193.233.232.48:8787/18-fix-chain.sh | sh -s 192.168.1.112 192.168.1.50

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
PC_IP="${1:-192.168.1.112}"
SALUT_IP="${2:-}"
XRAY_PORT=61219

# Остановить конкурирующий nfqws
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
/opt/etc/init.d/S99zapret2 stop 2>/dev/null || true

curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"
curl -fL -o /opt/etc/xray/configs/02_dns.json "$BASE/02_dns.json"
# Только Google/YouTube через VPS (all_vps ломает весь интернет)
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"

xkeen -restart
sleep 3

redirect_device() {
  ip="$1"
  [ -n "$ip" ] || return 0
  iptables -t mangle -D PREROUTING -s "$ip/32" -j xkeen 2>/dev/null || true
  iptables -t nat -D PREROUTING -s "$ip/32" -p tcp -j REDIRECT --to-ports "$XRAY_PORT" 2>/dev/null || true
  iptables -t nat -I PREROUTING 1 -s "$ip/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports "$XRAY_PORT"
  # QUIC в обход xray — гасим, браузер/TV перейдут на TCP
  iptables -D FORWARD -s "$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
  iptables -I FORWARD 1 -s "$ip/32" -p udp --dport 443 -j DROP
  echo "  REDIRECT+QUIC-block: $ip"
}

redirect_device "$PC_IP"
redirect_device "$SALUT_IP"

mkdir -p /opt/etc/xkeen
cat > /opt/etc/xkeen/fix_chain.sh << EOF
#!/bin/sh
PC=$PC_IP
SALUT=$SALUT_IP
PORT=$XRAY_PORT
redirect() {
  ip="\$1"
  [ -n "\$ip" ] || return 0
  iptables -t nat -D PREROUTING -s "\$ip/32" -p tcp -j REDIRECT --to-ports \$PORT 2>/dev/null || true
  iptables -t nat -I PREROUTING 1 -s "\$ip/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports \$PORT
  iptables -D FORWARD -s "\$ip/32" -p udp --dport 443 -j DROP 2>/dev/null || true
  iptables -I FORWARD 1 -s "\$ip/32" -p udp --dport 443 -j DROP
}
redirect "\$PC"
redirect "\$SALUT"
EOF
chmod +x /opt/etc/xkeen/fix_chain.sh

for f in /opt/etc/init.d/S*xkeen*; do
  [ -f "$f" ] || continue
  grep -q fix_chain.sh "$f" 2>/dev/null && break
  if grep -q "xkeen -start\|xkeen -restart" "$f" 2>/dev/null; then
    grep -q fix_chain.sh "$f" || sed -i '/xkeen/a /opt/etc/xkeen/fix_chain.sh' "$f" 2>/dev/null || true
    break
  fi
done

echo ""
echo "=== CHAIN FIX ==="
xkeen -status
echo ""
echo "NAT PREROUTING (счётчики должны расти при серфинге):"
iptables -t nat -L PREROUTING -n -v | head -10
echo ""
echo "VPS tunnel (должны быть ESTABLISHED :8443):"
netstat -an 2>/dev/null | grep 8443 | head -3 || ss -tn | grep 8443 | head -3
echo ""
echo "ПК: 2ip.ru -> 193.233.232.48, youtube.com -> видео"
echo "Салют: SmartTube -> любой ролик"
if [ -z "$SALUT_IP" ]; then
  echo ""
  echo "IP Салюта не задан. Keenetic Web -> СберТелек -> IP, затем:"
  echo "  curl -fsSL $BASE/18-fix-chain.sh | sh -s $PC_IP <IP_САЛЮТА>"
fi
