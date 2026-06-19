#!/bin/sh
# Скачать скрипты XKeen с VPS на Keenetic (без scp/SSH-ключей).
# На роутере: exec sh, затем одна строка ниже.
#
# curl -fsSL http://193.233.232.48:8787/00-router-pull.sh | sh

set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"

BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
DIR="${KEENETIC_XKEEN_DIR:-/tmp/xkeen}"

if ! command -v curl >/dev/null 2>&1; then
    echo "curl не найден — opkg install curl"
    exit 1
fi

mkdir -p "$DIR"
cd "$DIR"

for f in 02-nfqws2-standby.sh 03-install-xkeen.sh 04-start-xkeen.sh 04_outbounds.json; do
    echo "GET $f ..."
    curl -fL --connect-timeout 15 -m 120 -o "$f" "$BASE/$f"
done
chmod +x 02-nfqws2-standby.sh 03-install-xkeen.sh 04-start-xkeen.sh

echo ""
echo "=== Готово: $DIR ==="
ls -la "$DIR"
echo ""
echo "Дальше по порядку:"
echo "  sh $DIR/02-nfqws2-standby.sh"
echo "  sh $DIR/03-install-xkeen.sh"
echo "  # Keenetic Web: политика XKeen, ПК+Салют, DoH, ускоритель выкл"
echo "  sh $DIR/04-start-xkeen.sh"
