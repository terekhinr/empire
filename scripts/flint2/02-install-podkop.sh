#!/bin/sh
# Podkop (sing-box) — неинтерактивная установка.
set -eu

log() { printf '\033[1;32m[podkop]\033[0m %s\n' "$*"; }

if [ -x /etc/init.d/podkop ]; then
  log "podkop уже установлен"
  exit 0
fi

opkg update || true

# Русский интерфейс не ставим; https-dns-proxy — отказ если спросит
printf 'n\n' | sh -c "$(curl -fsSL https://raw.githubusercontent.com/itdoginfo/podkop/main/install.sh)" || {
  log "повтор без pipe..."
  PODKOP_NONINTERACTIVE=1 sh -c "$(curl -fsSL https://raw.githubusercontent.com/itdoginfo/podkop/main/install.sh)" </dev/null || true
}

[ -x /etc/init.d/podkop ] || { log "podkop не установился — проверьте opkg и место на eMMC"; exit 1; }
log "podkop OK"
