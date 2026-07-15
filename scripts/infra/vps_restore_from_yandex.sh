#!/usr/bin/env bash
# Восстановление Empire с Яндекс.Диска
# Usage: vps_restore_from_yandex.sh [latest|YYYY-MM-DD]
set -uo pipefail

REMOTE="${RCLONE_REMOTE:-yandex}"
HOST="$(hostname -s 2>/dev/null || echo vps)"
DAY="${1:-latest}"
REMOTE_BASE="${RCLONE_BACKUP_REMOTE_PATH:-VPS-backup}/${HOST}"
REMOTE_PATH="${REMOTE_BASE}/${DAY}"
ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
RESTORE_ROOT="${EMPIRE_RESTORE_ROOT:-$ROOT}"

log() { echo "[$(date -Iseconds)] $*"; }

if ! rclone listremotes 2>/dev/null | grep -q "^${REMOTE}:$"; then
  log "ERROR: нет remote ${REMOTE}. Настройте: scripts/rclone_setup_yandex_webdav.sh"
  exit 1
fi

if ! rclone lsd "${REMOTE}:${REMOTE_PATH}/" &>/dev/null; then
  log "ERROR: нет ${REMOTE}:${REMOTE_PATH}/"
  rclone lsd "${REMOTE}:${REMOTE_BASE}/" 2>/dev/null || true
  exit 1
fi

log "Restore from ${REMOTE}:${REMOTE_PATH}/ → ${RESTORE_ROOT}"

mkdir -p "$RESTORE_ROOT" /etc/empire /var/backups/empire

# Код
log "Downloading empire/ ..."
rclone copy "${REMOTE}:${REMOTE_PATH}/empire" "$RESTORE_ROOT" \
  --transfers 4 --checkers 8 --retries 10 -v

# /etc/empire
TMP="/var/tmp/empire-restore-$$"
mkdir -p "$TMP"
if rclone copy "${REMOTE}:${REMOTE_PATH}/etc-empire.tar.gz" "$TMP/" -v 2>/dev/null && [[ -f "$TMP/etc-empire.tar.gz" ]]; then
  log "Extracting /etc/empire ..."
  tar -xzf "$TMP/etc-empire.tar.gz" -C /etc
fi

# SQLite
if rclone lsd "${REMOTE}:${REMOTE_PATH}/sqlite-backups/" &>/dev/null; then
  log "Downloading sqlite-backups ..."
  rclone copy "${REMOTE}:${REMOTE_PATH}/sqlite-backups" /var/backups/empire/ -v --max-age 168h
  # latest db to project root
  for db in empire.db analytics.db sales.db portfolio.db; do
    latest=$(ls -t /var/backups/empire/*_${db} 2>/dev/null | head -1)
    [[ -n "$latest" ]] && cp -a "$latest" "${RESTORE_ROOT}/${db}" && log "restored ${db}"
  done
fi

# systemd
if rclone lsd "${REMOTE}:${REMOTE_PATH}/systemd/" &>/dev/null; then
  mkdir -p "$TMP/systemd"
  rclone copy "${REMOTE}:${REMOTE_PATH}/systemd" "$TMP/systemd" -v
  cp -a "$TMP/systemd/"* /etc/systemd/system/ 2>/dev/null || true
  systemctl daemon-reload 2>/dev/null || true
  log "systemd units copied — проверьте systemctl enable"
fi

# infra (home router, docs snapshot)
if rclone lsd "${REMOTE}:${REMOTE_PATH}/infra/" &>/dev/null; then
  mkdir -p "${RESTORE_ROOT}/data/infra"
  rclone copy "${REMOTE}:${REMOTE_PATH}/infra" "${RESTORE_ROOT}/data/infra" -v
  log "infra/ restored to data/infra/"
fi

rm -rf "$TMP"

log "=== RESTORE DONE ==="
log "Next steps:"
log "  1) cd ${RESTORE_ROOT} && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
log "  2) systemctl enable --now empire_main empire_gdepar ..."
log "  3) certbot nginx (TLS не в бэкапе)"
log "  4) docs/infra/VPS_RUNBOOK.md"
