#!/bin/bash
# Деплой протечка + Telegram на Home Assistant (Supervised на armbian).
# Запуск с машины, где лежит репо empire (или задайте EMPIRE_DIR).
#
#   cd /root/projects/empire
#   bash deploy/ha_deploy_telegram_protecka.sh
#
# Нужен SSH до armbian: root@192.168.1.41 (или HA_HOST=... HA_USER=...)

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-192.168.1.41}"
HA_USER="${HA_USER:-root}"
HA_CONFIG="${HA_CONFIG:-/config}"
SSH_TARGET="${HA_USER}@${HA_HOST}"

PKG_TELEGRAM="empire_telegram.yaml"
SECRETS_MARKER="ha_notify_url"

echo "==> Empire → HA (${SSH_TARGET}:${HA_CONFIG})"

ssh -o ConnectTimeout=10 "${SSH_TARGET}" "mkdir -p ${HA_CONFIG}/packages"

scp -q "${EMPIRE_DIR}/homeassistant/packages/${PKG_TELEGRAM}" \
  "${SSH_TARGET}:${HA_CONFIG}/packages/${PKG_TELEGRAM}"

echo "==> packages/${PKG_TELEGRAM} скопирован"

# secrets.yaml — дописать блок, если ещё нет ha_notify_url
ssh "${SSH_TARGET}" bash -s << 'REMOTE'
set -euo pipefail
CFG="/config"
SECRETS="${CFG}/secrets.yaml"
MARKER="ha_notify_url"

if [[ -f "$SECRETS" ]] && grep -q "$MARKER" "$SECRETS" 2>/dev/null; then
  echo "secrets.yaml: $MARKER уже есть — не трогаем"
else
  if [[ -f "$SECRETS" ]]; then
    cp -a "$SECRETS" "${SECRETS}.bak.$(date +%Y%m%d%H%M%S)"
  fi
  cat >> "$SECRETS" << 'EOF'

# --- empire telegram (deploy/ha_deploy_telegram_protecka.sh) ---
ha_notify_url: "http://172.30.32.1:8766/notify"
ha_notify_token: "Bearer ***REMOVED***"
EOF
  echo "secrets.yaml: добавлен блок empire telegram (+ backup если был файл)"
fi

# configuration.yaml — packages
if ! grep -q 'include_dir_named packages' "${CFG}/configuration.yaml" 2>/dev/null; then
  printf '\nhomeassistant:\n  packages: !include_dir_named packages\n' >> "${CFG}/configuration.yaml"
  echo "configuration.yaml: добавлен packages"
else
  echo "configuration.yaml: packages уже есть"
fi
REMOTE

echo "==> Если на HA уже есть empire_automations.yaml со старым rest_command —"
echo "    обновите его из репо (rest_command теперь только в empire_telegram.yaml)"

echo "==> Проверка моста с контейнера HA"
GW="${DOCKER_GW:-172.30.32.1}"
if ssh "${SSH_TARGET}" "docker exec homeassistant curl -sf -m 5 http://${GW}:8766/health" 2>/dev/null | grep -q ok; then
  echo "    health OK (gateway ${GW})"
else
  echo "    ВНИМАНИЕ: health не OK на ${GW}:8766"
  echo "    На armbian: systemctl status empire-ha-proxy empire-ha-bridge"
  echo "    Gateway: docker inspect homeassistant --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}'"
fi

echo ""
echo "==> В UI HA: Настройки → Система → YAML → Перезагрузить:"
echo "    - Автоматизации"
echo "    - Сценарии (script)"
echo "    - RESTful command (если есть пункт)"
echo ""
echo "    Тест: Сервисы → script.empire_test_telegram → Вызвать"
echo "    Протечка: binary_sensor.hobeian_zg_222z — при on → «Алярм! Тонем!»"
echo ""
echo "Готово."
