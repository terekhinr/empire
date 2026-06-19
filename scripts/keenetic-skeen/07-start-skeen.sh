#!/bin/sh
# Поднять SKeen после ребута / после 06-stop-skeen.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_SKEEN_BASE:-http://193.233.232.48:8787/skeen}"
WORK=/opt/etc/skeen
CFG=$WORK/config

echo "=== CHECK BINARIES ==="
if [ ! -x /opt/bin/skeen-box ]; then
  echo "ERROR: /opt/bin/skeen-box нет — запусти 01-install-skeen.sh"
  exit 1
fi
if [ ! -x /opt/bin/skeen ]; then
  curl -fL -o /opt/bin/skeen "https://github.com/jinndi/SKeen/releases/latest/download/skeen_ru" \
    || curl -fL -o /opt/bin/skeen "https://gh-proxy.com/https://github.com/jinndi/SKeen/releases/latest/download/skeen_ru"
  chmod 755 /opt/bin/skeen
fi
/opt/bin/skeen-box version

echo "=== CONFIG ==="
mkdir -p "$CFG"
curl -fL -o "$WORK/skeen.json" "$BASE/skeen.json"
for f in log.json dns.json inbounds.json outbounds.json route.json experimental.json; do
  curl -fL -o "$CFG/$f" "$BASE/$f"
done
# auto_start.enable уже 1 в skeen.json на сервере; НЕ sed по всему файлу (ломает redirect_dns)
/opt/bin/skeen-box format -w -C "$CFG"
/opt/bin/skeen-box check -D "$WORK" -C "$CFG" || { echo "CONFIG ERROR"; exit 1; }

echo "=== AUTOSTART init.d ==="
cat > /opt/etc/init.d/S99SKeen << 'EOF'
#!/bin/sh
PATH=/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin
sleep 10
/opt/bin/skeen start init
EOF
chmod 755 /opt/etc/init.d/S99SKeen

echo "=== START ==="
/opt/bin/skeen stop 2>/dev/null || true
killall skeen-box 2>/dev/null || true
sleep 2
/opt/bin/skeen start
sleep 5
/opt/bin/skeen status

echo ""
echo "=== DONE ==="
echo "Zashboard: http://192.168.1.1:9999"
echo "Keenetic: политика SKeen — Destroy_ + СберТелек"
echo "Сетевой ускоритель — ВЫКЛ"
