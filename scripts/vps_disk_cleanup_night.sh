#!/usr/bin/env bash
# Ночная выгрузка крупных файлов + TOX1 eMMC → Яндекс.Диск, затем очистка VPS.
# Запуск: systemd empire-disk-cleanup-night.timer (01:00 Europe/Moscow).
set -euo pipefail

ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
LOG_DIR="${EMPIRE_LOG_DIR:-/var/log/empire}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOCK="/var/lock/empire-disk-cleanup-night.lock"
SCRIPT="${ROOT}/scripts/vps_large_files_to_cloud.sh"

mkdir -p "$LOG_DIR"
exec >>"${LOG_DIR}/night-cleanup-${STAMP}.log" 2>&1

log() { echo "[$(date -Iseconds)] $*" >&2; }

exec 9>"$LOCK"
if ! flock -n 9; then
  log "SKIP: другой night-cleanup уже идёт"
  exit 0
fi

log "=== night-cleanup start (MSK $(TZ=Europe/Moscow date -Iseconds)) ==="

if [[ ! -x "$SCRIPT" ]]; then
  log "ERROR: нет $SCRIPT"
  exit 1
fi

# Убрать незавершённые части TOX1 (rcat не докачал — только sha256 или обрыв part000)
tox1_remote="yandex:VPS-backup/$(hostname -s 2>/dev/null || echo vps)/TOX1/parts/"
part_n="$(rclone lsf "$tox1_remote" 2>/dev/null | grep -c 'tox1-emmc-android-20260606.img.part' || true)"
if [[ "$part_n" -gt 0 && "$part_n" -lt 15 ]]; then
  log "Сброс неполного TOX1 на облаке (${part_n} частей) перед новой заливкой"
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    rclone deletefile "${tox1_remote}${f}" 2>/dev/null || true
  done < <(rclone lsf "$tox1_remote" 2>/dev/null | grep 'tox1-emmc-android-20260606.img.part' || true)
fi

log "--- 1/2 empire-large (media/data >80 МБ) ---"
"$SCRIPT" empire-large || { log "ERROR empire-large"; exit 1; }

log "--- 2/2 tox1-yandex (eMMC 30 ГБ) ---"
if [[ -f /root/tox1-backup/tox1-emmc-android-20260606.img ]]; then
  "$SCRIPT" tox1-yandex || { log "ERROR tox1-yandex"; exit 1; }
else
  log "SKIP tox1: образ уже выгружен / удалён"
fi

log "=== night-cleanup DONE ==="
