#!/bin/bash
# VPS: Tailscale SSH + стабильность Cursor Remote SSH. Идемпотентно.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="/root/.empire-ssh-backup"
STAMP="$(date +%Y%m%d-%H%M%S)"
log() { echo "[$(date -Iseconds)] tailscale_vps: $*"; }

mkdir -p "$BACKUP_DIR"

log "backup sshd snippets"
for f in /etc/ssh/sshd_config /etc/ssh/sshd_config.d/99-keepalive.conf; do
  [[ -f "$f" ]] && cp -a "$f" "$BACKUP_DIR/$(basename "$f").${STAMP}.bak"
done

log "keepalive sshd"
install -D -m 644 /dev/stdin /etc/ssh/sshd_config.d/99-keepalive.conf <<'EOF'
ClientAliveInterval 10
ClientAliveCountMax 60
TCPKeepAlive yes
EOF
sshd -t
systemctl reload ssh 2>/dev/null || systemctl reload sshd

log "tailscale RunSSH off (Cursor needs regular sshd + authorized_keys, not Tailscale SSH)"
if command -v tailscale >/dev/null 2>&1; then
  tailscale set --ssh=false 2>/dev/null || true
  tailscale ip -4 >"$BACKUP_DIR/tailscale-ip.${STAMP}.txt" 2>/dev/null || true
  log "tailscale ip: $(tailscale ip -4 2>/dev/null || echo n/a)"
else
  log "WARN: tailscale not installed"
fi

log "cursor orphan timer + xray healthcheck"
bash "$ROOT/scripts/apply_vps_ssh_stability.sh"

log "marker for rollback"
cat >"$BACKUP_DIR/ROLLBACK_README.${STAMP}.txt" <<EOF
Rollback VPS Tailscale SSH:
  bash $ROOT/scripts/rollback_vps_tailscale_ssh.sh

Backups in: $BACKUP_DIR
Applied: $(date -Iseconds)
EOF

log "done — PC next: powershell -File scripts/cursor_vps_tailscale_setup_pc.ps1"
