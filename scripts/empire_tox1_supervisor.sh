#!/usr/bin/env bash
# Держит TOX1-выгрузку живой: tmux + перезапуск если скрипт/rclone умер.
set -uo pipefail
ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
SESSION="${EMPIRE_TOX1_SESSION:-empire-tox1}"
IMG="/root/tox1-backup/tox1-emmc-android-20260606.img"

tox1_running() {
  pgrep -f 'vps_large_files_to_cloud.sh tox1-yandex' >/dev/null 2>&1 \
    || pgrep -f 'rclone copyto.*TOX1/parts/' >/dev/null 2>&1
}

if [[ ! -f "$IMG" ]]; then
  echo "[$(date -Iseconds)] TOX1: образ уже снят с VPS — OK"
  exit 0
fi

if tox1_running; then
  echo "[$(date -Iseconds)] TOX1: выгрузка уже идёт"
  exit 0
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux kill-session -t "$SESSION" 2>/dev/null || true
fi

tmux new-session -d -s "$SESSION" \
  "bash -lc 'cd \"$ROOT\" && while [[ -f \"$IMG\" ]]; do scripts/vps_large_files_to_cloud.sh tox1-yandex && break; echo RETRY; sleep 60; done; echo TOX1_DONE'"
echo "[$(date -Iseconds)] TOX1: запущен в tmux $SESSION"
