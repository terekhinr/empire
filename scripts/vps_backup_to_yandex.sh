#!/usr/bin/env bash
# Бэкап критичных данных VPS → Яндекс.Диск (не весь диск, без venv — ~2–3 ГБ).
set -euo pipefail

REMOTE="${RCLONE_REMOTE:-yandex}"
HOST="$(hostname -s 2>/dev/null || echo vps)"
DAY="$(date +%Y-%m-%d)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REMOTE_BASE="${RCLONE_BACKUP_REMOTE_PATH:-VPS-backup}/${HOST}"
REMOTE_DAY="${REMOTE_BASE}/${DAY}"
REMOTE_LATEST="${REMOTE_BASE}/latest"

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
LOCAL_DB_BACKUP="${EMPIRE_BACKUP_DIR:-/var/backups/empire}"
STAGING="/var/tmp/empire-vps-backup-${STAMP}"
ETC_TAR="${STAGING}/etc-empire.tar.gz"
SYSTEMD_STAGING="${STAGING}/systemd"

log() { echo "[$(date -Iseconds)] $*"; }

if [[ -x "$ROOT/scripts/guard_critical_files.sh" ]]; then
  log "Проверка целостности перед бэкапом..."
  "$ROOT/scripts/guard_critical_files.sh" || {
    log "ERROR: бэкап отменён — guard не прошёл (main.py и др.)"
    exit 1
  }
fi

if ! rclone listremotes 2>/dev/null | grep -q "^${REMOTE}:$"; then
  log "ERROR: нет remote ${REMOTE} — сначала scripts/rclone_setup_yandex_webdav.sh"
  exit 1
fi

mkdir -p "$STAGING" "$SYSTEMD_STAGING" "$LOCAL_DB_BACKUP"

# SQLite через существующий скрипт
if [[ -x "$ROOT/scripts/backup_empire_db.sh" ]]; then
  EMPIRE_ROOT="$ROOT" EMPIRE_BACKUP_DIR="$LOCAL_DB_BACKUP" "$ROOT/scripts/backup_empire_db.sh" || true
fi

if [[ -d /etc/empire ]]; then
  tar -czf "$ETC_TAR" -C /etc empire 2>/dev/null || true
fi

for u in /etc/systemd/system/empire*.service /etc/systemd/system/obsidian*.timer /etc/systemd/system/obsidian*.service; do
  [[ -f "$u" ]] && cp -a "$u" "$SYSTEMD_STAGING/" || true
done

log "Upload empire project (без venv) → ${REMOTE}:${REMOTE_DAY}/empire"
rclone copy "$ROOT" "${REMOTE}:${REMOTE_DAY}/empire" \
  --exclude "venv/**" \
  --exclude ".git/**" \
  --exclude "**/__pycache__/**" \
  --exclude "**/*.pyc" \
  --exclude "**/node_modules/**" \
  --exclude ".cursor/**" \
  --transfers 4 \
  --checkers 8 \
  -v

log "Upload /etc/empire + systemd + sqlite backups"
[[ -f "$ETC_TAR" ]] && rclone copy "$ETC_TAR" "${REMOTE}:${REMOTE_DAY}/" -v
[[ -d "$SYSTEMD_STAGING" ]] && rclone copy "$SYSTEMD_STAGING" "${REMOTE}:${REMOTE_DAY}/systemd" -v
rclone copy "$LOCAL_DB_BACKUP" "${REMOTE}:${REMOTE_DAY}/sqlite-backups" -v --max-age 48h

# «latest» — для быстрого восстановления
rclone sync "${REMOTE}:${REMOTE_DAY}" "${REMOTE}:${REMOTE_LATEST}" -v

# Дневные папки старше 14 дней
KEEP_DAYS="${EMPIRE_YANDEX_BACKUP_KEEP_DAYS:-14}"
CUTOFF="$(date -d "-${KEEP_DAYS} days" +%Y-%m-%d 2>/dev/null || date -v-${KEEP_DAYS}d +%Y-%m-%d 2>/dev/null || true)"
if [[ -n "$CUTOFF" ]]; then
  while IFS= read -r folder; do
    [[ -z "$folder" ]] && continue
    day="${folder%/}"
    [[ "$day" < "$CUTOFF" ]] || continue
    log "Удаляю старый архив: ${REMOTE}:${REMOTE_BASE}/${day}"
    rclone purge "${REMOTE}:${REMOTE_BASE}/${day}" 2>/dev/null || true
  done < <(rclone lsf "${REMOTE}:${REMOTE_BASE}/" --dirs-only 2>/dev/null || true)
fi

rm -rf "$STAGING"
log "DONE → yandex:${REMOTE_DAY} и yandex:${REMOTE_LATEST}"
