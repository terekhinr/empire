#!/bin/sh
# Восстановить SKeen/sing-box: конфиг, QUIC-block, watchdog, туннель на VPS.
# На роутере: exec curl -fsSL http://193.233.232.48:8787/10-revive-skeen.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_SKEEN_BASE:-http://193.233.232.48:8787/skeen}"
VPS="${KEENETIC_VPS:-193.233.232.48}"
WORK=/opt/etc/skeen
CFG=$WORK/config

echo "=== STOP CONFLICTS ==="
/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2
conntrack -D -p tcp --dport 8443 2>/dev/null || true
conntrack -D -p tcp --dst "$VPS" 2>/dev/null || true

echo "=== BINARIES ==="
if [ ! -x /opt/bin/skeen-box ]; then
  echo "ERROR: нет /opt/bin/skeen-box — сначала 01-install-skeen.sh"
  exit 1
fi
if [ ! -x /opt/bin/skeen ]; then
  curl -fL -o /opt/bin/skeen "https://github.com/jinndi/SKeen/releases/latest/download/skeen_ru" \
    || curl -fL -o /opt/bin/skeen "https://gh-proxy.com/https://github.com/jinndi/SKeen/releases/latest/download/skeen_ru"
  chmod 755 /opt/bin/skeen
fi
/opt/bin/skeen-box version

echo "=== VPS REACHABILITY ==="
if ! nc -z -w 5 "$VPS" 8443 2>/dev/null; then
  echo "WARN: VPS $VPS:8443 недоступен — sing-box поднимется, но туннель может не работать"
fi

echo "=== CONFIG ==="
mkdir -p "$CFG" /opt/var/log
curl -fL -o "$WORK/skeen.json" "$BASE/skeen.json"
for f in log.json dns.json inbounds.json outbounds.json route.json experimental.json; do
  curl -fL -o "$CFG/$f" "$BASE/$f"
done
/opt/bin/skeen-box format -w -C "$CFG"
/opt/bin/skeen-box check -D "$WORK" -C "$CFG" || { echo "CONFIG ERROR"; exit 1; }

echo "=== QUIC BLOCK (TCP-only YouTube) ==="
iptables -D FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true
iptables -I FORWARD -p udp --dport 443 -j DROP 2>/dev/null || true

echo "=== WATCHDOG ==="
WD=/opt/etc/skeen/watchdog.sh
cat > "$WD" << 'WEOF'
#!/bin/sh
export PATH="/opt/bin:/opt/sbin:$PATH"
n=$(netstat -tn 2>/dev/null | grep ':8443' | wc -l)
if [ "$n" -gt 35 ] || ! pidof skeen-box >/dev/null 2>&1; then
  conntrack -D -p tcp --dport 8443 2>/dev/null || true
  /opt/bin/skeen restart
fi
WEOF
chmod +x "$WD"
( crontab -l 2>/dev/null | grep -v skeen/watchdog; echo "*/10 * * * * $WD" ) | crontab -

echo "=== AUTOSTART ==="
cat > /opt/etc/init.d/S99SKeen << 'EOF'
#!/bin/sh
PATH=/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin
sleep 12
/opt/bin/skeen start init
EOF
chmod 755 /opt/etc/init.d/S99SKeen

echo "=== REVERSE SSH TUNNEL (для удалённого доступа) ==="
if [ -x /opt/etc/keenetic-tunnel/start.sh ]; then
  /opt/etc/keenetic-tunnel/start.sh || true
else
  curl -fsSL http://193.233.232.48:8787/19-router-access.sh | sh || true
fi

echo "=== START SKEEN ==="
/opt/bin/skeen start
sleep 6
netstat -tn 2>/dev/null | grep ':8443' | wc -l | xargs echo "tunnels:"
/opt/bin/skeen status

echo ""
echo "=== ГОТОВО ==="
echo "Zashboard: http://192.168.1.1:9999"
echo "Keenetic Web:"
echo "  • Политика «SKeen» — Destroy_ (112) + СберТелек (141)"
echo "  • Сетевой ускоритель — ВЫКЛ"
echo "  • Политику XKeen — удалить"
echo "YouTube: Ctrl+Shift+N, Amnezia на ПК — выкл"
