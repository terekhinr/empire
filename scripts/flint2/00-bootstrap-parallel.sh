#!/bin/sh
# Bootstrap БЕЗ смены LAN (Keenetic ещё на 192.168.1.1). Запуск на Flint.
set -eu
export FLINT2_BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"

log() { printf '\033[1;32m[flint2-parallel]\033[0m %s\n' "$*"; }
fetch() { curl -fL --retry 3 --retry-delay 2 "$1"; }

log "Flint parallel bootstrap (LAN не меняем)"

for step in 02-install-podkop.sh 03-config-podkop.sh 04-install-zapret2.sh \
  05-wireguard-server.sh 06-transmission.sh 07-router-tunnel.sh 08-migrate-keenetic.sh; do
  log "=== $step ==="
  fetch "$FLINT2_BASE/$step" | sh
done

fetch "$FLINT2_BASE/11-youtube-verify.sh" | sh || true
log "готово. LAN смена: curl .../01-base-lan.sh | sh — только при отключении Keenetic"
