#!/bin/sh
# Привязать ПК и Салют к политике NFQWS (Policy1).
# curl -fsSL http://193.233.232.48:8787/25-nfqws2-bind-policy.sh | sh
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

PC_MAC="${1:-94:de:80:64:ed:e6}"
SALUT_MAC="${2:-04:05:dd:c5:eb:a4}"
POLICY="${3:-Policy1}"

ndmc -c "ip hotspot host ${PC_MAC} policy ${POLICY}" 2>&1 || true
ndmc -c "ip hotspot host ${SALUT_MAC} policy ${POLICY}" 2>&1 || true
ndmc -c "ip hotspot policy Home ${POLICY}" 2>&1 || true
ndmc -c "system configuration save" 2>&1 || true
conntrack -F 2>/dev/null || true

echo "Policy ${POLICY}: PC ${PC_MAC}, Salut ${SALUT_MAC}"
echo "Keenetic: ускоритель ВЫКЛ, DoH Cloudflare 1.1.1.1"
