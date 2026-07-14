#!/bin/sh
# Полный бэкап Keenetic → файлы для восстановления на Flint.
# Запуск на VPS: ./scripts/flint2/keenetic-backup.sh
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== export Keenetic RCI ==="
python3 export-keenetic.py

echo "=== build snapshot + restore scripts ==="
python3 build-keenetic-snapshot.py

echo "=== files ==="
ls -la keenetic-export.json keenetic-snapshot.json keenetic-restore.env dhcp-static-leases.sh wifi-psk.txt 2>/dev/null

echo ""
echo "Восстановление на Flint одной командой:"
echo "  curl -fsSL http://193.233.232.48:8789/10-restore-keenetic-snapshot.sh | sh"
echo ""
echo "Или полный bootstrap (podkop + zapret + всё):"
echo "  curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh"
