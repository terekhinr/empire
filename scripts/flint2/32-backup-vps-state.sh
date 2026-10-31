#!/bin/sh
# Снимок состояния режима VPS для отката. Запуск на Flint.
set -eu
STAMP="${1:-$(date +%Y%m%d-%H%M%S)}"
BK="/etc/empire/rollback-vps/${STAMP}"
mkdir -p "$BK"

log() { echo "[backup-vps] $*"; }

log "→ $BK"

cp -a /etc/empire/bypass-mode "$BK/" 2>/dev/null || echo vps >"$BK/bypass-mode"
cp -a /etc/empire/bypass-state "$BK/" 2>/dev/null || echo vps >"$BK/bypass-state"
cp -a /etc/empire/vps.env "$BK/" 2>/dev/null || true
cp -a /etc/sing-box/config.json "$BK/" 2>/dev/null || true
cp -a /etc/podkop/sing-box.golden.json "$BK/" 2>/dev/null || true
cp -a /etc/crontabs/root "$BK/crontabs.root" 2>/dev/null || true
uci export podkop >"$BK/podkop.uci" 2>/dev/null || true
uci export dhcp >"$BK/dhcp.uci" 2>/dev/null || true
uci export firewall >"$BK/firewall.uci" 2>/dev/null || true

echo "$STAMP" > /etc/empire/rollback-vps/LATEST
log "OK stamp=$STAMP"
echo "$BK"
