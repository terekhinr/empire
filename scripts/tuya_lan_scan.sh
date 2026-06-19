#!/bin/bash
# Скан Tuya-устройств в локальной сети. Запускать на armbian или ПК в Wi‑Fi 192.168.1.x
set -euo pipefail

if ! python3 -c "import tinytuya" 2>/dev/null; then
  echo "Установка tinytuya..."
  python3 -m pip install --user tinytuya
fi

echo "=== Скан LAN (device_id, IP, версия) ==="
python3 -m tinytuya scan

echo ""
echo "Если список пуст — устройства в другой подсети или не Tuya."
echo "Ключи: python3 -m tinytuya wizard"
