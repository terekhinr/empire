#!/bin/sh
# ПК + Салют: REDIRECT TCP -> xray, только Google/YouTube через VPS. Остальное — direct.
# curl -fsSL http://193.233.232.48:8787/20-safe-fix.sh | sh
# curl -fsSL http://193.233.232.48:8787/20-safe-fix.sh | sh -s 192.168.1.112 192.168.1.141

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
PC_IP="${1:-192.168.1.112}"
SALUT_IP="${2:-192.168.1.141}"
PORT=61219

# geodata — без симлинков Google routing ломается (ERR_FAILED)
DAT=/opt/etc/xray/dat
for f in geosite_v2fly.dat geoip_v2fly.dat geosite_zkeen.dat geoip_zkeenip.dat; do
  ln -sf "$DAT/$f" /opt/sbin/$f 2>/dev/null || true
done

curl -fL --connect-timeout 10 -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"
curl -fL -o /opt/etc/xray/configs/02_dns.json "$BASE/02_dns.json"
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"

xkeen -restart
sleep 3

redirect_one() {
  ip="$1"
  [ -n "$ip" ] || return 0
  iptables -t nat -D PREROUTING -s "$ip/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports "$PORT" 2>/dev/null || true
  iptables -t nat -I PREROUTING 1 -s "$ip/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports "$PORT"
  echo "  REDIRECT $ip -> :$PORT"
}

redirect_one "$PC_IP"
redirect_one "$SALUT_IP"

mkdir -p /opt/etc/xkeen
cat > /opt/etc/xkeen/safe_fix.sh << EOF
#!/bin/sh
PC=$PC_IP
SALUT=$SALUT_IP
PORT=$PORT
r() {
  ip="\$1"
  [ -n "\$ip" ] || return 0
  iptables -t nat -D PREROUTING -s "\$ip/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports \$PORT 2>/dev/null || true
  iptables -t nat -I PREROUTING 1 -s "\$ip/32" ! -d 192.168.0.0/16 -p tcp -j REDIRECT --to-ports \$PORT
}
r "\$PC"
r "\$SALUT"
EOF
chmod +x /opt/etc/xkeen/safe_fix.sh

for f in /opt/etc/init.d/S*xkeen*; do
  [ -f "$f" ] || continue
  grep -q safe_fix.sh "$f" 2>/dev/null && break
  grep -q "xkeen -start\|xkeen -restart" "$f" 2>/dev/null && \
    grep -q safe_fix.sh "$f" || sed -i '/xkeen/a /opt/etc/xkeen/safe_fix.sh' "$f" 2>/dev/null || true
  break
done

echo ""
xkeen -status
iptables -t nat -L PREROUTING -n -v | head -6
echo ""
echo "ya.ru / youtube.com на ПК и Салюте. 2ip.ru = MTS (это норма)."
