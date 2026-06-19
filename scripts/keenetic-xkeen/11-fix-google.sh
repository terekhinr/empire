#!/bin/sh
# Gmail + YouTube + Google через VPS (gmail.com не был в zkeen — шёл напрямую в MTS)
# curl -fsSL http://193.233.232.48:8787/11-fix-google.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"
curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"
xkeen -restart
sleep 2
xkeen -status
echo ""
grep -E 'google|gmail|ytimg|geoip_zkeenip' /opt/etc/xray/configs/05_routing.json | head -8
echo ""
echo "ПК: ipconfig /flushdns, Chrome инкognito. Gmail + YouTube."
