#!/bin/sh
# Принудительный перехват XKeen для ПК (политика Keenetic не маркирует пакеты)
# curl -fsSL http://193.233.232.48:8787/16-force-pc.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
PC_IP="${1:-192.168.1.112}"

curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"
curl -fL -o /opt/etc/xray/configs/02_dns.json "$BASE/02_dns.json"

xkeen -restart
sleep 2

# Принудительно: весь TCP/UDP с ПК -> цепочка xkeen
iptables -t mangle -D PREROUTING -s "$PC_IP/32" -j xkeen 2>/dev/null || true
iptables -t mangle -I PREROUTING 1 -s "$PC_IP/32" -j xkeen

# Salut TV (если IP другой — добавь вторым скриптом)
# iptables -t mangle -I PREROUTING 1 -s 192.168.1.XXX/32 -j xkeen

mkdir -p /opt/etc/xkeen
cat > /opt/etc/xkeen/force_pc.sh << EOF
#!/bin/sh
iptables -t mangle -D PREROUTING -s $PC_IP/32 -j xkeen 2>/dev/null || true
iptables -t mangle -I PREROUTING 1 -s $PC_IP/32 -j xkeen
EOF
chmod +x /opt/etc/xkeen/force_pc.sh

# Автозапуск правила после xkeen
grep -q force_pc.sh /opt/etc/init.d/S98xkeen 2>/dev/null || true

echo "=== OK: force xkeen for $PC_IP ==="
xkeen -status
iptables -t mangle -L PREROUTING -n -v | head -6
echo ""
echo "ПК: ipconfig /renew && открой 2ip.ru (должен 193.233.232.48)"
