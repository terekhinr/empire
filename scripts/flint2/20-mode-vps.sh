#!/bin/sh
# Режим А: YouTube и блокировки РФ через VLESS (podkop), zapret как страховка WAN.
# Не смешивать одни и те же домены в FakeIP и nfqws — см. podkop diagnostics FakeIP.
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"
DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo .)"

log() { printf '\033[1;32m[mode-vps]\033[0m %s\n' "$*"; }

run_step() {
  name="$1"
  if [ -f "$DIR/$name" ]; then
    sh "$DIR/$name"
  else
    curl -fsSL "$BASE/$name" | sh
  fi
}

run_step 19-prereq-dpi.sh
run_step 02-install-podkop.sh
run_step 03-config-podkop.sh
run_step 04-install-zapret2.sh
run_step 22-configure-zapret.sh

mkdir -p /etc/empire
echo vps >/etc/empire/bypass-mode
echo vps >/etc/empire/bypass-state
cat >/etc/empire/vps.env <<'EOF'
VPS_HOST=193.233.232.48
VPS_PORT=8443
EOF

# В VPS-режиме YouTube идёт в туннель. Хостлист zapret остаётся для failover
# и для доменов, которые утекли на WAN. nfqws на FakeIP 198.18.x безвреден.

if [ -x /etc/flint2-tunnel/start.sh ]; then
  /etc/flint2-tunnel/start.sh 2>/dev/null || true
elif [ -f "$DIR/07-router-tunnel.sh" ]; then
  sh "$DIR/07-router-tunnel.sh" || true
fi

log "режим VPS. Проверка: curl -I https://www.youtube.com/generate_204"
log "диагностика podkop: LuCI → Services → Podkop → Diagnostics"
log "сторож: install-local.sh или с VPS install.sh"
