#!/usr/bin/env bash
# Бэкап критичных данных VPS → Яндекс.Диск (код + конфиг, без тяжёлого мусора).
set -uo pipefail

exec 9>/var/lock/empire-vps-backup.lock
if ! flock -n 9; then
  echo "[$(date -Iseconds)] SKIP: другой бэкап уже идёт"
  exit 0
fi

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

for u in /etc/systemd/system/empire*.service /etc/systemd/system/empire*.timer \
         /etc/systemd/system/obsidian*.timer /etc/systemd/system/obsidian*.service; do
  [[ -f "$u" ]] && cp -a "$u" "$SYSTEMD_STAGING/" || true
done

log "Сбор infra-пакета (docs, роутер, systemd)..."
if [[ -x "$ROOT/scripts/infra/infra_backup_bundle.sh" ]]; then
  EMPIRE_ROOT="$ROOT" "$ROOT/scripts/infra/infra_backup_bundle.sh" || log "WARN: infra_backup_bundle"
fi

log "Upload empire project (код, без venv/media/PDF/dist) → ${REMOTE}:${REMOTE_DAY}/empire"
# Полное дерево на WebDAV держало oneshot 4+ ч → SIGTERM. По умолчанию только sqlite+/etc.
if [[ "${EMPIRE_BACKUP_SKIP_FULL_TREE:-1}" == "1" ]]; then
  log "SKIP full tree copy (EMPIRE_BACKUP_SKIP_FULL_TREE=1)"
else
rclone copy "$ROOT" "${REMOTE}:${REMOTE_DAY}/empire" \
  --exclude "venv/**" \
  --exclude ".git/**" \
  --exclude "**/__pycache__/**" \
  --exclude "**/*.pyc" \
  --exclude "**/node_modules/**" \
  --exclude ".cursor/**" \
  --exclude "media/**" \
  --exclude "data/gdepar/**" \
  --exclude "data/audio/**" \
  --exclude "data/obsidian_vault/**" \
  --exclude "data/pension/**" \
  --exclude "content/**" \
  --exclude "kb_sources/**" \
  --exclude "vector_db/**" \
  --exclude "media/stern/technique_clips/**" \
  --exclude "desktop/**" \
  --exclude "scripts/keenetic-xkeen/blobs/**" \
  --exclude "*.pdf" \
  --exclude "**/*.pdf" \
  --exclude "*.PDF" \
  --exclude "**/*.epub" \
  --exclude "**/*.zip" \
  --exclude "**/*.img" \
  --exclude "**/*.iso" \
  --max-size 20M \
  --transfers 4 \
  --checkers 8 \
  --retries 5 \
  --low-level-retries 10 \
  --stats 2m \
  --stats-one-line \
  --timeout 2m \
  --contimeout 30s \
  -v || log "WARN: rclone copy empire — частичные ошибки (WebDAV)"
fi

# Yandex WebDAV по IPv6 часто зависает на PUT; bind IPv4.
RCLONE_BIND="${RCLONE_BIND:-0.0.0.0}"
rclone_yd() {
  rclone "$@" --bind "$RCLONE_BIND" --ignore-checksum --retries 1 --low-level-retries 2 --contimeout 30s
}

log "Upload /etc/empire + systemd + sqlite backups (сначала мелкие БД)"
[[ -f "$ETC_TAR" ]] && rclone_yd copy "$ETC_TAR" "${REMOTE}:${REMOTE_DAY}/" --timeout 2m -v || log "WARN: etc tar"
[[ -d "$SYSTEMD_STAGING" ]] && rclone_yd copy "$SYSTEMD_STAGING" "${REMOTE}:${REMOTE_DAY}/systemd" --timeout 2m -v || log "WARN: systemd"

SQLITE_LATEST="${STAGING}/sqlite-latest"
SQLITE_SMALL="${STAGING}/sqlite-small"
mkdir -p "$SQLITE_LATEST" "$SQLITE_SMALL"
for prefix in analytics sales; do
  newest="$(ls -1t "${LOCAL_DB_BACKUP}/${prefix}-"*.db 2>/dev/null | head -1 || true)"
  if [[ -n "$newest" && -f "$newest" ]]; then
    cp -a "$newest" "$SQLITE_LATEST/"
    cp -a "$newest" "$SQLITE_SMALL/"
  fi
done
if compgen -G "${SQLITE_SMALL}/*" >/dev/null; then
  rclone_yd copy "$SQLITE_SMALL" "${REMOTE}:${REMOTE_DAY}/sqlite-backups" --timeout 3m -v \
    || log "WARN: analytics/sales upload"
fi
# empire.db gzip: отдельный PUT, иначе мелкие файлы не уезжают
emp_newest="$(ls -1t "${LOCAL_DB_BACKUP}/empire-"*.db 2>/dev/null | head -1 || true)"
if [[ -n "$emp_newest" && -f "$emp_newest" ]]; then
  gzip -c "$emp_newest" > "${SQLITE_LATEST}/empire-latest.db.gz" || true
  if [[ -f "${SQLITE_LATEST}/empire-latest.db.gz" ]]; then
    timeout 8m rclone_yd copy "${SQLITE_LATEST}/empire-latest.db.gz" "${REMOTE}:${REMOTE_DAY}/sqlite-backups/" \
      --timeout 8m --transfers 1 -v \
      || log "WARN: empire.db.gz upload (локальная копия в ${LOCAL_DB_BACKUP})"
  fi
fi

# Infra: домашняя сеть, docs snapshot, rclone backup
if [[ -d "$ROOT/data/infra" ]]; then
  log "Upload data/infra → ${REMOTE}:${REMOTE_DAY}/infra"
  rclone_yd copy "$ROOT/data/infra" "${REMOTE}:${REMOTE_DAY}/infra" \
    --transfers 2 --checkers 4 --timeout 5m -v || log "WARN: infra upload"
fi

# latest: только sqlite/systemd/infra — НЕ sync всей дневной папки (старый empire/ даёт 412)
log "Обновляю latest (без дерева empire/)"
rclone_yd copy "${REMOTE}:${REMOTE_DAY}/sqlite-backups" "${REMOTE}:${REMOTE_LATEST}/sqlite-backups" --timeout 5m -v \
  || log "WARN: latest sqlite"
rclone_yd copy "${REMOTE}:${REMOTE_DAY}/systemd" "${REMOTE}:${REMOTE_LATEST}/systemd" --timeout 2m -v \
  || log "WARN: latest systemd"
rclone_yd copy "${REMOTE}:${REMOTE_DAY}/infra" "${REMOTE}:${REMOTE_LATEST}/infra" --timeout 5m -v \
  || log "WARN: latest infra"

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
