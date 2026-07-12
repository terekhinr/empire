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
  local part_mb="${TOX1_PART_MB:-2000}"
  local part_bytes=$((part_mb * 1024 * 1024))
  local img_size chunk="/var/tmp/tox1-chunk-upload"
  local prefix="tox1-emmc-android-20260606.img.part"

  [[ -f "$img" ]] || { log "ERROR: нет $img"; exit 1; }
  require_rclone

  img_size="$(stat -c%s "$img")"
  local total_parts=$(((img_size + part_bytes - 1) / part_bytes))
  log "=== TOX1 eMMC → ${remote}/parts/ (${part_mb} МБ × ~${total_parts} частей, ${img_size} байт) ==="

  sha256sum "$img" > "${img}.sha256"
  rclone copyto "${img}.sha256" "${remote}/parts/tox1-emmc-android-20260606.img.sha256" \
    --retries 10 -v

  local part_num=0 offset=0 uploaded=0
  while [[ "$offset" -lt "$img_size" ]]; do
    local name="${prefix}$(printf '%03d' "$part_num")"
    local this_size="$part_bytes"
    if [[ $((offset + this_size)) -gt "$img_size" ]]; then
      this_size=$((img_size - offset))
    fi

    if rclone lsf "${remote}/parts/${name}" >/dev/null 2>&1; then
      local csz
      csz="$(rclone lsl "${remote}/parts/${name}" 2>/dev/null | awk '{print $1}' | head -1)"
      csz="${csz:-0}"
      if [[ "$csz" -ge "$this_size" ]]; then
        log "SKIP ${name} — на облаке (${csz} байт)"
        offset=$((offset + this_size))
        part_num=$((part_num + 1))
        uploaded=$((uploaded + 1))
        continue
      fi
      log "WARN: ${name} неполный на облаке (${csz}/${this_size}), перезаливка"
      rclone deletefile "${remote}/parts/${name}" 2>/dev/null || true
    fi

    log ">>> Часть $((part_num + 1))/${total_parts}: ${name} (${this_size} байт, offset ${offset})"
    dd if="$img" of="$chunk" bs=1M skip=$((offset / 1048576)) \
      count=$(((this_size + 1048575) / 1048576)) status=progress

    # Без timeout: 2 ГБ при ~50 KiB/s ≈ 11–14 ч; 12h timeout сбрасывал part001 с нуля
    rclone copyto "$chunk" "${remote}/parts/${name}" \
      --ignore-checksum --size-only \
      --progress --stats 1m --stats-one-line \
      --retries 10 --low-level-retries 20 \
      --timeout 0 -v

    csz="$(rclone lsl "${remote}/parts/${name}" 2>/dev/null | awk '{print $1}' | head -1)"
    csz="${csz:-0}"
    if [[ "$csz" -lt "$this_size" ]]; then
      log "ERROR: ${name} не залит (${csz}/${this_size})"
      rm -f "$chunk"
      exit 1
    fi
    rm -f "$chunk"
    uploaded=$((uploaded + 1))
    log "OK ${name} залит (${uploaded}/${total_parts})"
    offset=$((offset + this_size))
    part_num=$((part_num + 1))
  done

  local cloud_n
  cloud_n="$(rclone lsf "${remote}/parts/" 2>/dev/null | grep -c "${prefix}" || true)"
  log "Частей на облаке: ${cloud_n}/${total_parts}"
  if [[ "$cloud_n" -lt "$total_parts" ]]; then
    log "ERROR: ожидалось ${total_parts} частей, получено ${cloud_n}"
    exit 1
  fi

  rm -f "$img" "${img}.sha256" "$chunk"
  log "DONE tox1-yandex: образ удалён с VPS (+30 ГБ)"
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
