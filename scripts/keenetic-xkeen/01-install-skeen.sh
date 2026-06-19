#!/bin/sh
# Неинтерактивная установка SKeen + sing-box на Keenetic Entware (mipsel).
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

BASE="${KEENETIC_SKEEN_BASE:-http://193.233.232.48:8787/skeen}"
SING_VER="${SING_BOX_VERSION:-1.12.12}"
PKG_ARCH="${SING_BOX_ARCH:-mipsel_mips32}"
WORK=/opt/etc/skeen
CFG=$WORK/config

echo "=== DEPS ==="
opkg update
for p in start-stop-daemon iptables ip-full ipset net-tools curl tar jsonfilter; do
  opkg install "$p" 2>/dev/null || true
done

echo "=== SING-BOX binary ==="
TMP=/opt/tmp/skeen-install
mkdir -p "$TMP"
cd "$TMP"
PKG="sing-box_${SING_VER}_openwrt_${PKG_ARCH}.ipk"
URL="https://github.com/SagerNet/sing-box/releases/download/v${SING_VER}/${PKG}"
curl -fL --connect-timeout 20 -m 300 -o "$PKG" "$URL" \
  || curl -fL --connect-timeout 20 -m 300 -o "$PKG" "https://gh-proxy.com/${URL}"

tar -xzf "$PKG"
tar -xzf data.tar.gz
install -m 755 ./usr/bin/sing-box /opt/bin/skeen-box
/opt/bin/skeen-box version

echo "=== SKEEN script ==="
curl -fL --connect-timeout 20 -m 120 -o /opt/bin/skeen \
  "https://github.com/jinndi/SKeen/releases/latest/download/skeen_ru" \
  || curl -fL -o /opt/bin/skeen "https://gh-proxy.com/https://github.com/jinndi/SKeen/releases/latest/download/skeen_ru"
chmod 755 /opt/bin/skeen

echo "=== CONFIG ==="
mkdir -p "$CFG"
curl -fL -o "$WORK/skeen.json" "$BASE/skeen.json"
for f in log.json dns.json inbounds.json outbounds.json route.json experimental.json; do
  curl -fL -o "$CFG/$f" "$BASE/$f"
done
/opt/bin/skeen-box format -w -C "$CFG"

echo "=== GROUP + AUTOSTART ==="
grep -q '^skeen:' /opt/etc/group 2>/dev/null || addgroup skeen 2>/dev/null || true
cat > /opt/etc/init.d/S99SKeen << 'EOF'
#!/bin/sh
PATH=/opt/sbin:/opt/bin:/usr/sbin:/usr/bin:/sbin:/bin
/opt/bin/skeen start init
EOF
chmod 755 /opt/etc/init.d/S99SKeen

echo "=== START ==="
/opt/bin/skeen start
sleep 3
/opt/bin/skeen status || true

echo ""
echo "=== DONE ==="
echo "Keenetic Web:"
echo "  1. Политика «SKeen» — добавь Destroy_ (192.168.1.112) и СберТелек (192.168.1.141)"
echo "  2. Сетевой ускоритель — ВЫКЛ"
echo "  3. DNS DoH — по желанию (Cloudflare/Yandex)"
echo "Zashboard: http://192.168.1.1:9999"
