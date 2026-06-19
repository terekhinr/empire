#!/bin/sh
# Chrome + Yandex + Salut TV: убрать блок QUIC, расширить Google-списки
# curl -fsSL http://193.233.232.48:8787/15-all-devices.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

curl -fL -o /opt/etc/xray/configs/02_dns.json "$BASE/02_dns.json"
curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"
curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"

xkeen -restart
sleep 3
xkeen -status
echo ""
grep geosite_v2fly /opt/etc/xray/configs/05_routing.json | head -2
grep 'port.*443' /opt/etc/xray/configs/05_routing.json && echo "WARN: блок 443 ещё есть!" || echo "OK: блок UDP/443 убран"
echo ""
echo "Keenetic Web: ПК + Salut TV только в XKeen"
echo "ПК: curl -I https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
