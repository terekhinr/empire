#!/usr/bin/env bash
# Подтянуть health-экспорты с Яндекс.Диска в data/pension/body/ и обновить SQLite.
#
# На Диске (создайте вручную):
#   Empire/health-inbox/garmin/Activities.csv   — экспорт Garmin
#   Empire/health-inbox/scale/BODY_*.csv        — весы (Zepp / Mi Fit / аналог)
#   Empire/health-inbox/food/food.csv           — дневник калорий
#
# Настройка:
#   sudo bash scripts/rclone_setup_yandex_webdav.sh
#   echo 'YANDEX_HEALTH_REMOTE_PATH=Empire/health-inbox' >> /etc/empire/rclone.env
#
# Cron (пример, 4 раза в день):
#   15 6,12,18,23 * * * /root/projects/empire/scripts/health_sync_from_yandex.sh >> /var/log/empire-health-sync.log 2>&1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BODY_DIR="$ROOT/data/pension/body"
ENV_FILE="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"
REMOTE="${YANDEX_REMOTE:-yandex:}"
INBOX="${YANDEX_HEALTH_REMOTE_PATH:-Empire/health-inbox}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone не установлен" >&2
  exit 1
fi

mkdir -p "$BODY_DIR"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "[$(date -Is)] pull $REMOTE$INBOX"
rclone copy "${REMOTE}${INBOX}" "$TMP/inbox" -v --include "/**" || {
  echo "Не удалось прочитать ${REMOTE}${INBOX} — проверьте rclone и путь" >&2
  exit 1
}

shopt -s nullglob
for f in "$TMP/inbox"/garmin/*.csv "$TMP/inbox"/garmin/**/*.csv; do
  cp -f "$f" "$BODY_DIR/Activities.csv"
  echo "  garmin → Activities.csv"
done
for f in "$TMP/inbox"/scale/BODY*.csv "$TMP/inbox"/scale/**/*.csv; do
  cp -f "$f" "$BODY_DIR/$(basename "$f")"
  echo "  scale → $(basename "$f")"
done
for f in "$TMP/inbox"/food/food.csv "$TMP/inbox"/food/**/*.csv; do
  cp -f "$f" "$BODY_DIR/food.csv"
  echo "  food → food.csv"
done

if [[ -x "$ROOT/venv/bin/python3" ]]; then
  "$ROOT/venv/bin/python3" - <<'PY'
from health_db import sync_csv_if_changed
result = sync_csv_if_changed(force=True)
print("health_db:", result)
PY
else
  echo "venv не найден — файлы скопированы, импорт при открытии дашборда"
fi

echo "[$(date -Is)] done"
