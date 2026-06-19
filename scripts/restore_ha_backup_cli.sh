#!/bin/bash
# Восстановление бэкапа HA без UI (обход 500 на загрузке).
# Использование на боксе:
#   bash restore_ha_backup_cli.sh /path/to/backup.tar
set -euo pipefail

BACKUP="${1:?Укажите путь к .tar бэкапу, например: /root/backup.tar}"

for d in /usr/share/hassio/backup /backup; do
  if [[ -d "$d" ]]; then
    DEST="$d"
    break
  fi
done
[[ -n "${DEST:-}" ]] || { echo "Каталог backup не найден"; exit 1; }

echo "Копируем $(basename "$BACKUP") -> $DEST/"
cp -v "$BACKUP" "$DEST/"
ha supervisor restart
sleep 15
echo "=== Список бэкапов (slug — короткий ID слева) ==="
ha backups list
echo ""
echo "Восстановление: ha backups restore <slug>"
echo "Пример: ha backups restore a1b2c3d4"
