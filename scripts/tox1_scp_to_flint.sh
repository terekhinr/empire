#!/usr/bin/env bash
# TOX1 eMMC образ VPS → USB на Flint (reverse SSH :6223).
set -euo pipefail

IMG="/root/tox1-backup/tox1-emmc-android-20260606.img"
SHA="${IMG}.sha256"
REMOTE="root@127.0.0.1:/mnt/usb/download/TOX1-backup/"
# Flint (dropbear): без -O scp требует sftp-server, которого нет.
SSH_OPTS=(-O -P 6223 -o StrictHostKeyChecking=no)
LOG="${EMPIRE_LOG_DIR:-/var/log/empire}/tox1-flint-scp.log"

mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1

log() { echo "[$(date -Iseconds)] $*"; }

[[ -f "$IMG" ]] || { log "ERROR: нет $IMG"; exit 1; }

log "=== TOX1 → Flint USB ($REMOTE) ==="
log "sha256 first"
scp "${SSH_OPTS[@]}" "$SHA" "$REMOTE"

log "image start ($(stat -c%s "$IMG") bytes)"
scp "${SSH_OPTS[@]}" "$IMG" "$REMOTE"

log "=== DONE ==="
