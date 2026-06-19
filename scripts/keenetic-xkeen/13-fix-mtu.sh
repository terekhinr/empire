#!/bin/sh
# Google/YouTube: MTU fix + IPIfNonMatch (DNS xray уже есть)
# curl -fsSL http://193.233.232.48:8787/13-fix-mtu.sh | sh

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
grep tcpMaxSeg /opt/etc/xray/configs/04_outbounds.json || true
grep domainStrategy /opt/etc/xray/configs/05_routing.json || true
