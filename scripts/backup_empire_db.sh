#!/usr/bin/env bash
# Ежедневный бэкап SQLite (ТЗ FINAL §6 фаза 0). Cron:
#   15 3 * * * root /root/projects/empire/scripts/backup_empire_db.sh
set -euo pipefail
ROOT="${EMPIRE_ROOT:-/root/projects/empire}"
DEST="${EMPIRE_BACKUP_DIR:-/var/backups/empire}"
KEEP_DAYS="${EMPIRE_BACKUP_KEEP_DAYS:-14}"
mkdir -p "$DEST"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
for db in empire.db analytics.db sales.db; do
  src="$ROOT/$db"
  [[ -f "$src" ]] || continue
  out="$DEST/${db%.db}-$STAMP.db"
  sqlite3 "$src" ".backup '$out'"
  echo "OK $out"
done
find "$DEST" -name '*.db' -mtime +"$KEEP_DAYS" -delete 2>/dev/null || true
