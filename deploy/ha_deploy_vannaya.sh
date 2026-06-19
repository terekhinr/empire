#!/bin/bash
# Деплой ванной (motion + dimmer template) на HA.
#   cd /root/projects/empire && bash deploy/ha_deploy_vannaya.sh
#
# SSH: HA_HOST (по умолчанию 192.168.1.41). С Tailscale с ПК: HA_HOST=100.80.133.85

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-192.168.1.41}"
HA_USER="${HA_USER:-root}"
HA_CONFIG="${HA_CONFIG:-/usr/share/hassio/homeassistant}"
SSH_TARGET="${HA_USER}@${HA_HOST}"

PKGS=(
  empire_motion_light.yaml
  empire_vannaya_dimmer_fix.yaml
)

echo "==> Ванная → ${SSH_TARGET}:${HA_CONFIG}/packages/"
ssh -o ConnectTimeout=15 "${SSH_TARGET}" "mkdir -p ${HA_CONFIG}/packages"

for f in "${PKGS[@]}"; do
  scp -q "${EMPIRE_DIR}/homeassistant/packages/${f}" \
    "${SSH_TARGET}:${HA_CONFIG}/packages/${f}"
  echo "    ${f}"
done

echo ""
echo "==> В UI HA: Панель разработчика → YAML → Перезагрузить:"
echo "    Автоматизации, Сценарии, Шаблоны (Template)"
echo ""
echo "==> Проверка с ПК (если есть .env):"
echo "    set -a && source .env && set +a && python3 tools/ha_vannaya_diagnose.py"
echo ""
echo "Готово."
