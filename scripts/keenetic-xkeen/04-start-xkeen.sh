#!/bin/sh
# Запуск XKeen после настройки 04_outbounds.json
set -eu

export PATH="/opt/bin:/opt/sbin:$PATH"

if ! grep -q '"address":' /opt/etc/xray/configs/04_outbounds.json 2>/dev/null \
   || grep -q '"address": ""' /opt/etc/xray/configs/04_outbounds.json 2>/dev/null; then
    echo "ОШИБКА: заполни /opt/etc/xray/configs/04_outbounds.json (vless://)"
    exit 1
fi

/opt/etc/init.d/S51nfqws2 stop 2>/dev/null || true
xkeen -start

echo "=== Статус ==="
xkeen -status 2>/dev/null || ps w | grep -i xray | grep -v grep | head -3
echo ""
echo "Тест: youtube.com на ПК (инкогнито), Сбер — напрямую"
