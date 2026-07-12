#!/usr/bin/env bash
# Единый ночной пайплайн VPS (01:00 МСК ≈ 22:00 UTC):
#   1) SQLite-бэкап
#   2) TOX1 eMMC → Я.Диск (освобождает ~30 ГБ — ПЕРВЫМ, не ждёт Я.Диск)
#   3) Код/config → Я.Диск (лёгкий, без тяжёлых PDF/dist)
#   4) Крупные media/data → Я.Диск (фон)
#   5) Очистка staging /var/tmp
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

log "--- 1/5 SQLite ---"
if [[ -x "$ROOT/scripts/backup_empire_db.sh" ]]; then
  EMPIRE_ROOT="$ROOT" "$ROOT/scripts/backup_empire_db.sh" || log "WARN: sqlite backup failed"
fi

log "--- 2/5 TOX1 eMMC (приоритет: освободить 30 ГБ) ---"
if [[ -f /root/tox1-backup/tox1-emmc-android-20260606.img ]]; then
  if pgrep -f 'vps_large_files_to_cloud.sh tox1-yandex' >/dev/null 2>&1 \
    || pgrep -f 'rclone copyto.*TOX1/parts/' >/dev/null 2>&1; then
    log "SKIP tox1: выгрузка уже идёт"
  elif [[ -x "$ROOT/scripts/empire_tox1_supervisor.sh" ]]; then
    "$ROOT/scripts/empire_tox1_supervisor.sh" || log "WARN: tox1 supervisor failed"
  else
    "$ROOT/scripts/vps_large_files_to_cloud.sh" tox1-yandex || log "WARN: tox1-yandex failed"
  fi
else
  log "SKIP tox1: образ уже выгружен"
fi

log "--- 3/5 код → Я.Диск ---"
if [[ -f /root/tox1-backup/tox1-emmc-android-20260606.img ]]; then
  log "SKIP yandex code: TOX1 eMMC ещё на VPS — не конкурируем с выгрузкой"
elif [[ -x "$ROOT/scripts/vps_backup_to_yandex.sh" ]]; then
  "$ROOT/scripts/vps_backup_to_yandex.sh" || log "WARN: yandex backup failed"
fi

log "--- 4/5 empire-large (>80 МБ media/data) ---"
if [[ -f /root/tox1-backup/tox1-emmc-android-20260606.img ]]; then
  log "SKIP empire-large: TOX1 eMMC ещё на VPS"
elif [[ -x "$ROOT/scripts/vps_large_files_to_cloud.sh" ]]; then
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

log "--- 5/5 очистка staging + git snapshot ---"
if [[ -x "$ROOT/scripts/empire_vps_git_snapshot.sh" ]]; then
  "$ROOT/scripts/empire_vps_git_snapshot.sh" || true
fi
find /var/tmp -maxdepth 1 -type d -name 'empire-large-*' -mtime +2 -exec rm -rf {} + 2>/dev/null || true
find /var/tmp -maxdepth 1 -type d -name 'empire-vps-backup-*' -mtime +1 -exec rm -rf {} + 2>/dev/null || true
find /var/tmp -maxdepth 1 -type d -name 'tox1-parts-*' -mtime +1 -exec rm -rf {} + 2>/dev/null || true

log "=== night pipeline DONE ==="
