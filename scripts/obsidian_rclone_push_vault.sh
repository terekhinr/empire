#!/usr/bin/env bash
# Vault VPS → Яндекс.Диск (copy — не удаляет файлы, которых нет на VPS).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

REMOTE="${RCLONE_REMOTE:-yandex}"
REMOTE_VAULT="${RCLONE_VAULT_REMOTE_PATH:-obsidian (2)}"
VAULT_ROOT="${OBSIDIAN_VAULT_ROOT:-$ROOT/data/obsidian_vault}"

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone не установлен" >&2
  exit 1
fi

# sync: VPS = источник правды после уборки агента (copy оставлял старые файлы в облаке).
rclone sync "$VAULT_ROOT" "${REMOTE}:${REMOTE_VAULT}" \
  --fast-list \
  --exclude ".gemini/**" \
  --exclude ".obsidian/**" \
  --ignore-errors \
  -v

echo "Vault copied → ${REMOTE}:${REMOTE_VAULT}"
