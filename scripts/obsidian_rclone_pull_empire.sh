#!/usr/bin/env bash
# Empire/: Яндекс.Диск → VPS (правки queue с ПК через клиент Диска).
# Отдельно от pull всего vault (там Empire/ исключён, чтобы не затирать агента).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
[[ -f /etc/empire/empire.env ]] && source /etc/empire/empire.env

REMOTE="${RCLONE_REMOTE:-yandex}"
REMOTE_PATH="${RCLONE_REMOTE_PATH:-obsidian (2)/Empire}"
LOCAL="${OBSIDIAN_VAULT_EMPIRE:-$ROOT/data/obsidian_vault/Empire}"

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone не установлен" >&2
  exit 1
fi

mkdir -p "$LOCAL"
rclone sync "${REMOTE}:${REMOTE_PATH}" "$LOCAL" \
  --fast-list \
  --exclude ".obsidian/**" \
  --exclude "**/published/**" \
  -v

echo "Pulled Empire → $LOCAL"
