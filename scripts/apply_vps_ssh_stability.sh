#!/bin/bash
# Одноразовое применение всех server-side фиксов стабильности SSH/Cursor (VPS).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
log() { echo "[$(date -Iseconds)] apply_stability: $*"; }

log "reload sshd (ClientAlive 10s)"
sshd -t
systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true

log "cursor orphan cleanup"
bash "$ROOT/scripts/cursor_orphan_cleanup.sh" || true

log "timers"
install -D -m 644 "$ROOT/deploy/cursor-orphan-cleanup.service" /etc/systemd/system/cursor-orphan-cleanup.service
install -D -m 644 "$ROOT/deploy/cursor-orphan-cleanup.timer" /etc/systemd/system/cursor-orphan-cleanup.timer
systemctl daemon-reload
systemctl enable --now cursor-orphan-cleanup.timer empire-memory-refresh.timer 2>/dev/null || true

log "xray healthcheck cron"
if crontab -l 2>/dev/null | grep -q 'xray-healthcheck'; then
  crontab -l | sed 's|^\*/2 \* \* \* \* .*xray-healthcheck.sh|*/10 * * * * '"$ROOT"'/scripts/keenetic-xkeen/xray-healthcheck.sh|' | crontab -
fi

log "sshd ClientAlive: $(sshd -T 2>/dev/null | awk '/^clientaliveinterval/{print $2}')s interval, max $(sshd -T 2>/dev/null | awk '/^clientalivecountmax/{print $2}')"
log "tailscale: $(tailscale ip -4 2>/dev/null || echo n/a)"
log "free: $(free -h | awk '/^Mem:/{print $7}') available"
log "done"
