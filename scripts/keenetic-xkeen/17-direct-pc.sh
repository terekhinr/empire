#!/bin/sh
# Прямой REDIRECT TCP с ПК на xray (минуя сломанную маркировку Keenetic)
# curl -fsSL http://193.233.232.48:8787/17-direct-pc.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
PC_IP="${1:-192.168.1.112}"
XRAY_PORT=61219

curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"
curl -fL -o /opt/etc/xray/configs/02_dns.json "$BASE/02_dns.json"

xkeen -restart
sleep 2

# Убрать старые костыли
iptables -t mangle -D PREROUTING -s "$PC_IP/32" -j xkeen 2>/dev/null || true
iptables -t nat -D PREROUTING -s "$PC_IP/32" -p tcp -j REDIRECT --to-ports $XRAY_PORT 2>/dev/null || true

# Весь TCP с ПК (кроме LAN) -> xray transparent proxy
iptables -t nat -I PREROUTING 1 -s "$PC_IP/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports $XRAY_PORT

mkdir -p /opt/etc/xkeen
cat > /opt/etc/xkeen/direct_pc.sh << EOF
#!/bin/sh
PC=$PC_IP
PORT=$XRAY_PORT
iptables -t nat -D PREROUTING -s \$PC/32 -p tcp -j REDIRECT --to-ports \$PORT 2>/dev/null || true
iptables -t nat -I PREROUTING 1 -s \$PC/32 ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports \$PORT
EOF
chmod +x /opt/etc/xkeen/direct_pc.sh

# Подключить к init xkeen если есть hook
for f in /opt/etc/init.d/S*xkeen*; do
  [ -f "$f" ] || continue
  grep -q direct_pc.sh "$f" 2>/dev/null && break
  if grep -q "xkeen -start" "$f" 2>/dev/null; then
    grep -q "direct_pc.sh" "$f" || sed -i '/xkeen -start/a /opt/etc/xkeen/direct_pc.sh' "$f" 2>/dev/null || true
    break
  fi
done

echo "=== DIRECT REDIRECT $PC_IP -> :$XRAY_PORT ==="
xkeen -status
iptables -t nat -L PREROUTING -n -v | head -8
echo ""
echo "ПК: ipconfig /renew → 2ip.ru → 193.233.232.48 → youtube"
