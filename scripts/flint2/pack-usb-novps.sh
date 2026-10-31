#!/bin/sh
# Собрать каталог для USB: режим без VPS + сторож.
# Запуск на VPS/ПК: sh scripts/flint2/pack-usb-novps.sh [DEST]
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-/tmp/flint-novps-usb}"

rm -rf "$DEST"
mkdir -p "$DEST/empire-flint-watchdog"

for f in 00-bootstrap-novps.sh 01-base-lan.sh 04-install-zapret2.sh \
  19-prereq-dpi.sh 21-mode-novps.sh 22-configure-zapret.sh \
  11-youtube-verify.sh zapret-hosts.txt torrent-domains.txt README.txt; do
  [ -f "$ROOT/$f" ] && cp -a "$ROOT/$f" "$DEST/"
done

cp -a "$ROOT/empire-flint-watchdog/." "$DEST/empire-flint-watchdog/"
# PWA иконки большие — оставляем, на USB места хватит
cat >"$DEST/START.txt" <<'EOF'
1. Скопируйте ВЕСЬ этот каталог на USB (FAT32/NTFS).
2. Вставьте USB в Flint, SSH: ssh root@192.168.1.1
3. Найдите диск: ls /mnt  или  block info
4. sh /mnt/usb/flint-novps-usb/00-bootstrap-novps.sh
   (путь поправьте под фактический mount)
5. LuCI → Services → Zapret. При необходимости: zms
EOF

echo "USB kit → $DEST"
echo "скопируйте на флешку и запустите 00-bootstrap-novps.sh на Flint"
