#!/bin/bash
# VPS: откат изменений apply_vps_tailscale_ssh.sh (sshd keepalive, опционально RunSSH).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="/root/.empire-ssh-backup"
log() { echo "[$(date -Iseconds)] rollback_vps: $*"; }

disable_ssh=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --disable-tailscale-ssh) disable_ssh=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--disable-tailscale-ssh]"
      echo "  Restores latest sshd backup; removes 99-keepalive.conf if no backup."
      echo "  --disable-tailscale-ssh  also: tailscale set --ssh=false"
      exit 0
      ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

latest_keepalive="$(ls -t "$BACKUP_DIR"/99-keepalive.conf.*.bak 2>/dev/null | head -1 || true)"
if [[ -n "$latest_keepalive" ]]; then
  log "restore $latest_keepalive -> /etc/ssh/sshd_config.d/99-keepalive.conf"
  cp -a "$latest_keepalive" /etc/ssh/sshd_config.d/99-keepalive.conf
else
  log "no keepalive backup — remove /etc/ssh/sshd_config.d/99-keepalive.conf"
  rm -f /etc/ssh/sshd_config.d/99-keepalive.conf
fi

sshd -t
systemctl reload ssh 2>/dev/null || systemctl reload sshd

if $disable_ssh && command -v tailscale >/dev/null 2>&1; then
  log "tailscale set --ssh=false"
  tailscale set --ssh=false 2>/dev/null || true
fi

log "done (PC rollback: scripts/cursor_vps_tailscale_rollback_pc.ps1)"
