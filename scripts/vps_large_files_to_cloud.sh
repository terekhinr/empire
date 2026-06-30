#!/usr/bin/env bash
# Крупные файлы empire + бэкап TOX1 eMMC → Яндекс.Диск (и опционально Google Drive).
# После успешной выгрузки — удаление локальных копий для освобождения места.
set -euo pipefail

REMOTE="${RCLONE_REMOTE:-yandex}"
HOST="$(hostname -s 2>/dev/null || echo vps)"
ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
MIN_MB="${EMPIRE_LARGE_MIN_MB:-80}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${EMPIRE_LOG_DIR:-/var/log/empire}"
LOCK="/var/lock/empire-large-cloud.lock"

mkdir -p "$LOG_DIR"
exec >>"${LOG_DIR}/large-files-cloud-${STAMP}.log" 2>&1

log() { echo "[$(date -Iseconds)] $*" >&2; }

require_rclone() {
  if ! rclone listremotes 2>/dev/null | grep -q "^${REMOTE}:$"; then
    log "ERROR: нет remote ${REMOTE}"
    exit 1
  fi
}

upload_tox1_yandex() {
  local img="/root/tox1-backup/tox1-emmc-android-20260606.img"
  local remote="${REMOTE}:VPS-backup/${HOST}/TOX1"
  local parts="/var/tmp/tox1-parts-${STAMP}"
  local part_size="${TOX1_PART_SIZE:-2000M}"

  [[ -f "$img" ]] || { log "ERROR: нет $img"; exit 1; }
  require_rclone

  log "=== TOX1 eMMC → ${remote}/parts/ (по ${part_size}, streaming) ==="
  mkdir -p "$parts"
  sha256sum "$img" > "${img}.sha256"
  rclone copyto "${img}.sha256" "${remote}/parts/tox1-emmc-android-20260606.img.sha256" \
    --retries 10 --timeout 0 -v

  # split --filter: данные на stdin, FILE — имя части (файл на диске пустой)
  split -b "$part_size" -d -a 3 "$img" "${parts}/tox1-emmc-android-20260606.img.part" \
    --filter='rclone rcat "'"${remote}"'/parts/$(basename "$FILE")" --timeout 0 --retries 10 -v'

  local cloud_n
  cloud_n="$(rclone lsf "${remote}/parts/" 2>/dev/null | grep -c 'tox1-emmc-android-20260606.img.part' || true)"
  log "Частей на облаке: ${cloud_n}"
  if [[ "$cloud_n" -lt 10 ]]; then
    log "ERROR: ожидалось ≥10 частей, получено ${cloud_n}"
    exit 1
  fi

  rm -rf "$parts"
  rm -f "$img" "${img}.sha256"
  log "DONE tox1-yandex: образ удалён с VPS после выгрузки"
}

stage_empire_large() {
  local staging="/var/tmp/empire-large-${STAMP}"
  local manifest="${staging}/MANIFEST.tsv"
  mkdir -p "$staging"
  : >"$manifest"

  log "Сканирование ${ROOT} (>${MIN_MB} МБ, data/ media/)..."
  while IFS= read -r -d '' f; do
    local rel="${f#${ROOT}/}"
    local dest="${staging}/${rel}"
    mkdir -p "$(dirname "$dest")"
    if [[ ! -e "$dest" ]]; then
      cp -a "$f" "$dest"
    fi
    printf '%s\t%s\n' "$f" "$rel" >>"$manifest"
  done < <(
    find "$ROOT/data" "$ROOT/media" -type f -size +"${MIN_MB}M" -print0 2>/dev/null
  )

  local n
  n="$(wc -l <"$manifest" | tr -d ' ')"
  log "В staging: ${n} файлов → ${staging}"
  echo "$staging"
}

upload_empire_large() {
  local staging
  staging="$(stage_empire_large)"
  local remote="${REMOTE}:VPS-backup/${HOST}/large-archive/${STAMP}/"
  local manifest="${staging}/MANIFEST.tsv"

  require_rclone
  log "=== Крупные media/data → ${remote} ==="
  rclone copy "$staging" "$remote" \
    --exclude 'MANIFEST.tsv' \
    --progress --stats 5m --stats-one-line \
    --transfers 4 --checkers 8 --timeout 0 -v

  rclone copyto "$manifest" "${remote}MANIFEST.tsv" --timeout 0 -v

  local ok=1
  while IFS=$'\t' read -r orig rel; do
    [[ -z "$orig" ]] && continue
    if ! rclone lsf "${remote}${rel}" >/dev/null 2>&1; then
      log "WARN: на облаке нет ${rel}"
      ok=0
    fi
  done <"$manifest"

  if [[ "$ok" -ne 1 ]]; then
    log "ERROR: не все файлы на облаке — локальные копии НЕ удаляем"
    exit 1
  fi

  while IFS=$'\t' read -r orig _rel; do
    [[ -z "$orig" ]] && continue
    rm -f "$orig"
    log "Удалён локально: ${orig}"
  done <"$manifest"
  rm -rf "$staging"
  log "DONE empire-large → ${remote}"
}

upload_tox1_gdrive() {
  local img="/root/tox1-backup/tox1-emmc-android-20260606.img"
  [[ -f "$img" ]] || { log "SKIP gdrive: нет $img"; exit 0; }
  log "=== TOX1 eMMC → gdrive:TOX1/ (≈30 ГБ) ==="
  rclone copyto "$img" "gdrive:TOX1/tox1-emmc-android-20260606.img" \
    --progress --stats 5m --stats-one-line --transfers 1 --timeout 0 --retries 10 -v
  log "DONE tox1-gdrive"
}

case "${1:-empire-large}" in
  tox1-yandex) upload_tox1_yandex ;;
  tox1-gdrive) upload_tox1_gdrive ;;
  empire-large)
    exec 9>"$LOCK"
    if ! flock -n 9; then
      log "SKIP: другой empire-large уже идёт"
      exit 0
    fi
    upload_empire_large
    ;;
  *)
    echo "Usage: $0 {empire-large|tox1-yandex|tox1-gdrive}" >&2
    exit 2
    ;;
esac
