#!/bin/sh
# Zapret2 — DPI-обход (аналог nfqws2 на Keenetic).
set -eu

log() { printf '\033[1;32m[zapret2]\033[0m %s\n' "$*"; }

if [ -x /etc/init.d/zapret2 ] || [ -x /etc/init.d/zapret ]; then
  log "zapret уже установлен"
  /etc/init.d/zapret2 restart 2>/dev/null || /etc/init.d/zapret restart 2>/dev/null || true
  exit 0
fi

opkg update || true
opkg install curl ca-bundle ca-certificates 2>/dev/null || true

curl -fsSL https://raw.githubusercontent.com/remittor/zapret-openwrt/zap1/zapret/update-pkg.sh -o /tmp/zap.sh
sh /tmp/zap.sh -u 2
rm -f /tmp/zap.sh

if [ -x /etc/init.d/zapret2 ]; then
  /etc/init.d/zapret2 enable
  /etc/init.d/zapret2 start
  log "zapret2 OK — откройте LuCI → Services → Zapret2, выберите пресет провайдера (МТС) и Restart"
elif [ -x /etc/init.d/zapret ]; then
  /etc/init.d/zapret enable
  /etc/init.d/zapret start
  log "zapret v1 OK"
else
  log "zapret не установился — установите вручную из GitHub releases (aarch64_cortex-a53)"
  exit 1
fi

# QUIC через podkop уже режется; дополнительно — как на Keenetic
if command -v nft >/dev/null 2>&1; then
  nft list chain inet fw4 forward 2>/dev/null | grep -q 'udp dport 443' || \
    nft insert rule inet fw4 forward iifname "br-lan" udp dport 443 drop 2>/dev/null || true
fi
