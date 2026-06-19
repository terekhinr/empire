#!/usr/bin/env bash
# После правок vault агентом на VPS: импорт в очередь + push Empire в облако.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ -f /etc/empire/empire.env ]] && source /etc/empire/empire.env

export OBSIDIAN_EMPIRE_INCOMING="${OBSIDIAN_EMPIRE_INCOMING:-$ROOT/data/obsidian_vault/Empire}"
"$ROOT/venv/bin/python" "$ROOT/scripts/sync_empire_obsidian.py" --all
"$ROOT/venv/bin/python" "$ROOT/scripts/import_obsidian_queue.py"
"$ROOT/scripts/obsidian_rclone_push.sh"
"$ROOT/scripts/obsidian_rclone_push_vault.sh"
