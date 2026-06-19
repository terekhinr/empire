#!/bin/sh
# Offline XKeen install via VPS (when GitHub blocked on router)
set -eu
export PATH=/opt/bin:/opt/sbin:$PATH
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

echo "=== XKeen + Xray с VPS ==="
mkdir -p /opt/etc/xray/configs /tmp/xkeen-off

curl -fL -o /tmp/xkeen-off/xkeen.tar.gz "$BASE/xkeen.tar.gz"
tar -xzf /tmp/xkeen-off/xkeen.tar.gz -C /opt/sbin

curl -fL -o /opt/sbin/xray "$BASE/xray-mips32le"
chmod +x /opt/sbin/xray /opt/sbin/xkeen

mkdir -p /tmp/xkeen
curl -fL -o /tmp/xkeen/xray.zip "$BASE/xray-upx.zip"

curl -fL -o /opt/etc/xray/configs/03_inbounds.json "$BASE/03_inbounds.json"
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"
curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"

rm -rf /tmp/xkeen-off
echo "OK: xkeen + xray + configs"
echo "Дальше: xkeen -i  (Xray → 0 пропустить, GeoIP 1, GeoSite 1)"
