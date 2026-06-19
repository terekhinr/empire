#!/usr/bin/env bash
# Obsidian vault: Яндекс.Диск → VPS (ПК / облако — источник правды при pull).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
[[ -f /etc/empire/empire.env ]] && source /etc/empire/empire.env

REMOTE="${RCLONE_REMOTE:-yandex}"
REMOTE_VAULT="${RCLONE_VAULT_REMOTE_PATH:-obsidian (2)}"
VAULT_ROOT="${OBSIDIAN_VAULT_ROOT:-$ROOT/data/obsidian_vault}"

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone не установлен: sudo apt install -y rclone" >&2
  exit 1
fi

mkdir -p "$VAULT_ROOT"
# --ignore-errors: на Linux часть имён из «База знаний» длиннее 255 байт (Windows OK).
# Empire/ на VPS ведёт агент → push в облако; pull всего vault не должен удалять новые файлы Empire.
rclone sync "${REMOTE}:${REMOTE_VAULT}" "$VAULT_ROOT" \
  --fast-list \
  --exclude ".obsidian/**" \
  --exclude "**/published/**" \
  --exclude "Empire/**" \
  --ignore-errors \
  -v

echo "Pulled → $VAULT_ROOT"

# Queue с ПК: Empire/ не входит в pull vault (см. --exclude выше).
if [[ -x "$ROOT/scripts/obsidian_rclone_pull_empire.sh" ]]; then
  bash "$ROOT/scripts/obsidian_rclone_pull_empire.sh" || true
fi

if [[ -x "$ROOT/venv/bin/python" ]]; then
  export OBSIDIAN_EMPIRE_INCOMING="${OBSIDIAN_EMPIRE_INCOMING:-$VAULT_ROOT/Empire}"
  if [[ -d "$OBSIDIAN_EMPIRE_INCOMING" ]]; then
    "$ROOT/venv/bin/python" "$ROOT/scripts/import_obsidian_queue.py" || true
  fi
fi
