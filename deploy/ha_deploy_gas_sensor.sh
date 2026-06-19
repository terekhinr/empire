#!/bin/bash
# Датчик газа Tuya TS0601 _TZE284_chbyv06x: custom ZHA quirk + Telegram + дашборд.
#
#   cd /root/projects/empire
#   bash deploy/ha_deploy_gas_sensor.sh
#
# SSH: HA_HOST=100.80.133.85 (Tailscale, порт 22222 = Terminal & SSH addon)

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_USER="${HA_USER:-root}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
HA_CONFIG="${HA_CONFIG:-/config}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -o StrictHostKeyChecking=no -i ${HOME}/.ssh/id_ed25519 -p ${HA_SSH_PORT}"
SSH_TARGET="${HA_USER}@${HA_HOST}"
QUIRK_DIR="${HA_CONFIG}/custom_zha_quirks"
QUIRK_FILE="tze284_chbyv06x_gas.py"

echo "==> Empire → HA gas sensor (${SSH_TARGET})"

if [[ -f "${EMPIRE_DIR}/.env" ]]; then
  set -a && source "${EMPIRE_DIR}/.env" && set +a
fi

echo "==> API: область «Кухня», диагностика"
PYTHON="${EMPIRE_DIR}/venv/bin/python3"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON=python3
fi
"${PYTHON}" "${EMPIRE_DIR}/tools/ha_gas_sensor_setup.py" || true

echo ""
echo "==> Файлы на ${SSH_TARGET} (нужен SSH)"
if ! ssh ${SSH_OPTS} "${SSH_TARGET}" "mkdir -p ${HA_CONFIG}/packages ${HA_CONFIG}/custom_zha_quirks"; then
  echo ""
  echo "SSH недоступен. Вручную через File editor на HA (/config/…):"
  echo "  1) custom_zha_quirks/${QUIRK_FILE}  ← empire/homeassistant/custom_zha_quirks/${QUIRK_FILE}"
  echo "  2) packages/empire_telegram.yaml"
  echo "  3) В configuration.yaml (если ещё нет):"
  echo "     zha:"
  echo "       custom_quirks_path: /config/custom_zha_quirks"
  echo "  4) Настройки → Система → Перезапуск Home Assistant"
  echo "  5) ZHA → «Датчик газа» → ⋮ → Удалить → Добавить устройство (permit 60 с)"
  echo "  6) YAML → Перезагрузить автоматизации"
  exit 0
fi

scp -q -o BatchMode=yes -o StrictHostKeyChecking=no -i "${HOME}/.ssh/id_ed25519" -P "${HA_SSH_PORT}" \
  "${EMPIRE_DIR}/homeassistant/custom_zha_quirks/${QUIRK_FILE}" \
  "${SSH_TARGET}:${QUIRK_DIR}/${QUIRK_FILE}"
scp -q -o BatchMode=yes -o StrictHostKeyChecking=no -i "${HOME}/.ssh/id_ed25519" -P "${HA_SSH_PORT}" \
  "${EMPIRE_DIR}/homeassistant/packages/empire_telegram.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/packages/empire_telegram.yaml"

ssh ${SSH_OPTS} "${SSH_TARGET}" bash -s << REMOTE
set -euo pipefail
CFG="${HA_CONFIG}/configuration.yaml"
if [[ -f "\$CFG" ]] && ! grep -q 'custom_quirks_path' "\$CFG" 2>/dev/null; then
  printf '\n# Tuya gas _TZE284_chbyv06x (deploy/ha_deploy_gas_sensor.sh)\nzha:\n  custom_quirks_path: /config/custom_zha_quirks\n' >> "\$CFG"
  echo "configuration.yaml: добавлен custom_quirks_path"
elif grep -q 'custom_quirks_path' "\$CFG" 2>/dev/null; then
  echo "configuration.yaml: custom_quirks_path уже есть"
fi
REMOTE

echo ""
echo "==> Дальше в UI HA:"
echo "    1) Настройки → Система → Перезапуск Home Assistant"
echo "    2) ZHA → «Датчик газа» → Удалить → Добавить устройство (60 с, кнопка на датчике)"
echo "    3) Проверка: binary_sensor.kukhnia_datchik_gaza"
echo "    4) YAML → Перезагрузить автоматизации"
echo "    5) Тест: кнопка «Тест» на датчике → Telegram «Алярм! Утечка газа!»"
echo ""
echo "Готово."
