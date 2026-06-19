#!/usr/bin/env bash
# Empire/: VPS → Яндекс.Диск (после правок агента на VPS; ПК подхватит клиентом Диска).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

REMOTE="${RCLONE_REMOTE:-yandex}"
REMOTE_PATH="${RCLONE_REMOTE_PATH:-obsidian (2)/Empire}"
LOCAL="${OBSIDIAN_VAULT_EMPIRE:-$ROOT/data/obsidian_vault/Empire}"

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone не установлен: sudo apt install -y rclone" >&2
  exit 1
fi

if [[ ! -d "$LOCAL" ]]; then
  echo "Нет каталога Empire на VPS: $LOCAL" >&2
  exit 1
fi

rclone sync "$LOCAL" "${REMOTE}:${REMOTE_PATH}" \
  --fast-list \
  --exclude ".obsidian/**" \
  -v

echo "Pushed → ${REMOTE}:${REMOTE_PATH}"
