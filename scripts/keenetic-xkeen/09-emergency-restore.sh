#!/bin/sh
# Экстренный откат: всегда качаем актуальный routing с VPS (не .bak — там мог быть all-vps / IPIfNonMatch)
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"

curl -fL -o /opt/etc/xray/configs/05_routing.json "$BASE/05_routing.json"
curl -fL -o /opt/etc/xray/configs/04_outbounds.json "$BASE/04_outbounds.json"

xkeen -restart
sleep 2
xkeen -status
echo ""
echo "OK. curl С РОУТЕРА (/ #) не тестирует XKeen — он идёт напрямую в MTS."
echo "Проверяй YouTube на ПК (инкognito)."
