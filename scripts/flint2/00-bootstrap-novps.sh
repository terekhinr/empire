#!/bin/sh
# Полный прогон режима БЕЗ Empire VPS. Запуск на Flint:
#   USB:  sh /mnt/usb/flint-novps/00-bootstrap-novps.sh
#   или скопировать каталог scripts/flint2 на роутер.
set -eu
export FLINT2_BASE="${FLINT2_BASE:-}"
DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo .)"
export FLINT2_DIR="$DIR"

log() { printf '\033[1;32m[novps]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[novps] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

run_step() {
  name="$1"
  if [ -f "$DIR/$name" ]; then
    log "=== $name (local) ==="
    sh "$DIR/$name"
  elif [ -n "$FLINT2_BASE" ]; then
    log "=== $name ($FLINT2_BASE) ==="
    curl -fL --retry 3 "$FLINT2_BASE/$name" | sh
  else
    die "нет файла $name и не задан FLINT2_BASE. Скопируйте scripts/flint2 на USB."
  fi
}

if [ -f /etc/openwrt_release ]; then
  . /etc/openwrt_release
  major="${DISTRIB_RELEASE%%.*}"
  [ "$major" = "24" ] || [ "$major" = "25" ] || die "нужна vanilla OpenWrt 24.10+"
else
  die "не OpenWrt"
fi

skip_lan=0
CURRENT="$(uci -q get network.lan.ipaddr || echo '')"
[ "$CURRENT" = "192.168.1.1" ] && skip_lan=1

[ "$skip_lan" = "1" ] || run_step 01-base-lan.sh
run_step 19-prereq-dpi.sh
run_step 04-install-zapret2.sh
run_step 22-configure-zapret.sh
run_step 21-mode-novps.sh

if [ -f "$DIR/empire-flint-watchdog/install-local.sh" ]; then
  log "=== watchdog local ==="
  sh "$DIR/empire-flint-watchdog/install-local.sh"
fi

if [ -f "$DIR/11-youtube-verify.sh" ]; then
  sh "$DIR/11-youtube-verify.sh" || true
fi

log "готово. LuCI http://192.168.1.1  → Services → Zapret"
log "подбор стратегии: zms (Zapret-Manager)"
log "сторож: /usr/sbin/empire-flint-watchdog --check"
