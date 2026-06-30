#!/usr/bin/env bash
# Снять зависший night-pipeline / rclone и запустить свежий пайплайн.
set -euo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
LOG_DIR="${EMPIRE_LOG_DIR:-/var/log/empire}"
MAX_AGE_H="${EMPIRE_STALE_PIPELINE_H:-20}"
FORCE="${EMPIRE_UNBLOCK_FORCE:-0}"

log() { echo "[$(date -Iseconds)] $*"; }

stale_age_h() {
  local pid="$1"
  local secs
  secs=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ' || echo 0)
  echo $((secs / 3600))
}

log "=== empire unblock backups (force=${FORCE}) ==="

for pid in $(pgrep -f 'empire_night_pipeline.sh' 2>/dev/null || true); do
  age=$(stale_age_h "$pid")
  if [[ "$FORCE" == "1" ]] || [[ "$age" -ge "$MAX_AGE_H" ]]; then
    log "KILL night-pipeline PID=$pid (${age}h)"
    kill "$pid" 2>/dev/null || true
  fi
done

for pid in $(pgrep -f 'vps_backup_to_yandex.sh|rclone copy.*/empire' 2>/dev/null || true); do
  age=$(stale_age_h "$pid")
  if [[ "$FORCE" == "1" ]] || [[ "$age" -ge 2 ]]; then
    log "KILL yandex rclone PID=$pid (${age}h)"
    kill "$pid" 2>/dev/null || true
  fi
done

sleep 2
for pid in $(pgrep -f 'empire_night_pipeline.sh|vps_backup_to_yandex|rclone copy.*/empire' 2>/dev/null || true); do
  kill -9 "$pid" 2>/dev/null || true
done

rm -f /var/lock/empire-night-pipeline.lock /var/lock/empire-large-cloud.lock /var/lock/empire-vps-backup.lock

if tmux has-session -t empire-backups 2>/dev/null; then
  tmux kill-session -t empire-backups 2>/dev/null || true
fi

log "Запуск свежего night-pipeline (TOX1 первым) в tmux empire-backups"
tmux new-session -d -s empire-backups \
  "bash -lc 'cd \"$ROOT\" && EMPIRE_ROOT=\"$ROOT\" \"$ROOT/scripts/empire_night_pipeline.sh\"; echo DONE; sleep 5'"

log "Лог: tail -f ${LOG_DIR}/night-pipeline-latest.log"
