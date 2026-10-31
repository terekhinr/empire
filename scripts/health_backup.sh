#!/bin/bash
# Бэкап health.db + загруженные программы на этот же VPS (+ опционально Яндекс.Диск).
set -euo pipefail
cd /root/projects/empire
ZIP="$(/root/projects/empire/venv/bin/python - <<'PY'
from health_backup import create_health_backup
print(create_health_backup())
PY
)"
echo "$ZIP"
if [[ "${HEALTH_BACKUP_YANDEX:-1}" == "1" ]] && command -v rclone >/dev/null 2>&1; then
  REMOTE="${RCLONE_REMOTE:-yandex}"
  HOST="$(hostname -s 2>/dev/null || echo vps)"
  DEST="${REMOTE}:VPS-backup/${HOST}/health/"
  echo "Upload → ${DEST}"
  rclone copy "$ZIP" "$DEST"
fi
