#!/bin/sh
# Flint 2 (GL-MT6000): полная настройка после vanilla OpenWrt 24.10.
# Запуск на роутере: curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh
set -eu
export FLINT2_BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[flint2]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[flint2] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

fetch() {
  u="$1"
  curl -fL --retry 3 --retry-delay 2 "$u"
}

need_openwrt24() {
  . /etc/openwrt_release 2>/dev/null || die "не OpenWrt"
  major="${DISTRIB_RELEASE%%.*}"
  if [ "$major" != "24" ] && [ "$major" != "25" ]; then
    die "нужна vanilla OpenWrt 24.10+ (сейчас ${DISTRIB_RELEASE:-?}). См. docs/FLINT2_SETUP.md — прошивка sysupgrade."
  fi
}

log "модель: $(cat /tmp/sysinfo/model 2>/dev/null || echo '?')"
need_openwrt24

for step in 01-base-lan.sh 02-install-podkop.sh 03-config-podkop.sh 04-install-zapret2.sh \
  05-wireguard-server.sh 06-transmission.sh 07-router-tunnel.sh; do
  log "=== $step ==="
  fetch "$FLINT2_BASE/$step" | sh
done

log "=== готово ==="
log "LuCI: http://192.168.1.1  |  Podkop: Services → Podkop"
log "Zapret2: Services → Zapret2 → Start"
log "WG-клиент: /etc/wireguard/clients/phone.conf"
log "VPS SSH: ssh -p 6223 root@127.0.0.1  (после туннеля с роутера)"
