#!/bin/sh
# conform + nfqws2 heal (без Policy1/SKeen).
# curl -fsSL http://193.233.232.48:8787/25-nfqws2-bind-policy.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

PC_MAC="${1:-94:de:80:64:ed:e6}"
SALUT_MAC="${2:-04:05:dd:c5:eb:a4}"

ndmc -c "ip hotspot host ${PC_MAC} conform" 2>&1 || true
ndmc -c "ip hotspot host ${SALUT_MAC} conform" 2>&1 || true
ndmc -c "system configuration save" 2>&1 || true
conntrack -F 2>/dev/null || true

curl -fsSL "$BASE/55-minimal-nfqws2.sh" | sh 2>/dev/null || true
if [ -x /opt/etc/keenetic-tunnel/start.sh ]; then
  /opt/etc/keenetic-tunnel/start.sh 2>/dev/null || true
fi

echo "conform: PC ${PC_MAC}, Salut ${SALUT_MAC}"
echo "Keenetic: ускоритель ВЫКЛ"
