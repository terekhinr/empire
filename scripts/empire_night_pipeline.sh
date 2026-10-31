#!/usr/bin/env bash
# Единый ночной пайплайн VPS (01:00 МСК ≈ 22:00 UTC):
#   1) SQLite-бэкап
#   2) Код/config/infra → Я.Диск
#   3) Крупные media/data → Я.Диск (фон)
#   4) Очистка staging /var/tmp
# TOX1: на USB Flint — в пайплайне не трогаем.
set -uo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
LOG_DIR="${EMPIRE_LOG_DIR:-/var/log/empire}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOCK="/var/lock/empire-night-pipeline.lock"
LARGE_LOCK="/var/lock/empire-large-cloud.lock"

mkdir -p "$LOG_DIR"

log() { echo "[$(date -Iseconds)] $*"; }

exec 9>"$LOCK"
if ! flock -n 9; then
  log "SKIP: другой night-pipeline уже идёт" >>"${LOG_DIR}/night-pipeline-skip.log"
  exit 0
fi

exec >>"${LOG_DIR}/night-pipeline-${STAMP}.log" 2>&1
ln -sf "${LOG_DIR}/night-pipeline-${STAMP}.log" "${LOG_DIR}/night-pipeline-latest.log"

log "=== empire night pipeline (MSK $(TZ=Europe/Moscow date -Iseconds)) ==="

log "--- 1/4 SQLite ---"
if [[ -x "$ROOT/scripts/backup_empire_db.sh" ]]; then
  EMPIRE_ROOT="$ROOT" "$ROOT/scripts/backup_empire_db.sh" || log "WARN: sqlite backup failed"
fi

log "--- 2/4 код + infra → Я.Диск (sqlite gzip + /etc; без полного дерева) ---"
if [[ -x "$ROOT/scripts/infra/infra_backup_bundle.sh" ]]; then
  EMPIRE_ROOT="$ROOT" "$ROOT/scripts/infra/infra_backup_bundle.sh" || log "WARN: infra bundle"
fi
if [[ -x "$ROOT/scripts/vps_backup_to_yandex.sh" ]]; then
  EMPIRE_BACKUP_SKIP_FULL_TREE=1 "$ROOT/scripts/vps_backup_to_yandex.sh" || log "WARN: yandex backup failed"
fi

log "--- 3/4 empire-large (>80 МБ media/data) ---"
if [[ -x "$ROOT/scripts/vps_large_files_to_cloud.sh" ]]; then
  if pgrep -f 'vps_large_files_to_cloud.sh empire-large' >/dev/null 2>&1 \
    || pgrep -f 'large-archive/' >/dev/null 2>&1; then
    log "SKIP empire-large: выгрузка уже идёт (фон)"
  else
    exec 8>"$LARGE_LOCK"
    if flock -n 8; then
      nohup "$ROOT/scripts/vps_large_files_to_cloud.sh" empire-large \
        >>"${LOG_DIR}/empire-large-nohup-${STAMP}.log" 2>&1 &
      log "empire-large запущен в фоне PID=$!"
    else
      log "SKIP empire-large: lock занят"
    fi
  fi
fi

log "--- 4/4 очистка staging (без git add -A: 23G дерево вешает oneshot) ---"
find /var/tmp -maxdepth 1 -type d -name 'empire-large-*' -mtime +2 -exec rm -rf {} + 2>/dev/null || true
find /var/tmp -maxdepth 1 -type d -name 'empire-vps-backup-*' -mtime +1 -exec rm -rf {} + 2>/dev/null || true
find /var/tmp -maxdepth 1 -type d -name 'tox1-parts-*' -mtime +1 -exec rm -rf {} + 2>/dev/null || true

log "=== night pipeline DONE ==="
