#!/usr/bin/env bash
# Синхронизация Life/tasks с Яндекс.Диска для дашборда «Планирование».
#
# На Диске: Life/tasks/inbox.md (ваш Obsidian vault)
# На VPS:  data/obsidian_vault/Life/tasks/
#
# Cron:
#   30 */2 * * * /root/projects/empire/scripts/planning_sync_from_yandex.sh >> /var/log/empire-planning-sync.log 2>&1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"
REMOTE="${YANDEX_REMOTE:-yandex:}"
TASKS_PATH="${YANDEX_LIFE_TASKS_PATH:-Life/tasks}"
TARGET="$ROOT/data/obsidian_vault/Life/tasks"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

mkdir -p "$TARGET"

echo "[$(date -Is)] sync ${REMOTE}${TASKS_PATH} → $TARGET"
rclone copy "${REMOTE}${TASKS_PATH}" "$TARGET" -v \
  --include "inbox.md" \
  --include "dashboard.md" \
  --include "dashboard-sync.md" \
  --include "_import/**"

if [[ -x "$ROOT/venv/bin/python3" ]]; then
  "$ROOT/venv/bin/python3" - <<'PY'
from planning_db import import_obsidian_inbox, export_obsidian_sync
imp = import_obsidian_inbox()
exp = export_obsidian_sync()
print("planning:", {"import": imp, "export_rows": exp})
PY
fi

echo "[$(date -Is)] done"
