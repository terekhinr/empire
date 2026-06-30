#!/bin/bash
# Настенная панель Empire + тема + пакет Ezviz.
#
#   cd /root/projects/empire && bash deploy/ha_deploy_wall_dashboard.sh
#
# Перед деплоем: добавьте Ezviz в HA (см. docs/HA_EZVIZ_WALL_DASHBOARD.md)
# и переименуйте camera.* → ezviz_ulica / ezviz_podezd.

set -euo pipefail

EMPIRE_DIR="${EMPIRE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
HA_HOST="${HA_HOST:-100.80.133.85}"
HA_USER="${HA_USER:-root}"
HA_SSH_PORT="${HA_SSH_PORT:-22222}"
HA_CONFIG="${HA_CONFIG:-/config}"
SSH_OPTS="-o ConnectTimeout=12 -o BatchMode=yes -o StrictHostKeyChecking=no -i ${HOME}/.ssh/id_ed25519"
SCP_OPTS="${SSH_OPTS} -P ${HA_SSH_PORT}"
SSH_TARGET="${HA_USER}@${HA_HOST}"

echo "==> Загрузка темы, дашборда, пакета Ezviz"
ssh ${SSH_OPTS} -p "${HA_SSH_PORT}" "${SSH_TARGET}" "mkdir -p ${HA_CONFIG}/themes ${HA_CONFIG}/dashboards ${HA_CONFIG}/packages"
scp -q ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/themes/empire_wall.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/themes/empire_wall.yaml"
scp -q ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/dashboards/empire_wall.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/dashboards/empire_wall.yaml"
scp -q ${SCP_OPTS} \
  "${EMPIRE_DIR}/homeassistant/packages/empire_ezviz.yaml" \
  "${SSH_TARGET}:${HA_CONFIG}/packages/empire_ezviz.yaml"

echo "==> Патч configuration.yaml (themes + lovelace empire-wall)"
TMP_CFG="/tmp/ha_configuration_empire_wall.yaml"
scp -q ${SCP_OPTS} "${SSH_TARGET}:${HA_CONFIG}/configuration.yaml" "${TMP_CFG}"
cp -a "${TMP_CFG}" "${TMP_CFG}.bak"

python3 - "${TMP_CFG}" <<'PY'
import re
import sys
from pathlib import Path

cfg = Path(sys.argv[1])
text = cfg.read_text()
changed = False

if "!include_dir_merge_named themes" not in text:
    if re.search(r"^frontend:\s*$", text, re.M):
        text = re.sub(
            r"(^frontend:\s*\n)",
            r"\1  themes: !include_dir_merge_named themes\n",
            text,
            count=1,
            flags=re.M,
        )
    else:
        text = text.rstrip() + "\n\nfrontend:\n  themes: !include_dir_merge_named themes\n"
    changed = True
    print("  + frontend.themes")

if "empire-wall" not in text or re.search(r"^zha:\n  custom_quirks_path:.*\n    empire-wall:", text, re.M):
    wall_block = (
        "    empire-wall:\n"
        "      mode: yaml\n"
        "      title: Панель\n"
        "      icon: mdi:tablet-dashboard\n"
        "      show_in_sidebar: true\n"
        "      require_admin: false\n"
        "      filename: dashboards/empire_wall.yaml\n"
    )
    # Убрать ошибочный empire-wall под zha (старый баг деплоя)
    text2 = re.sub(
        r"(?ms)^zha:\n  custom_quirks_path:.*\n(?:    empire-wall:.*\n(?:      .*\n)*)",
        "zha:\n  custom_quirks_path: /config/custom_zha_quirks\n",
        text,
    )
    if text2 != text:
        text = text2
        changed = True
        print("  fix zha block")
    if "empire-wall" not in text:
        if "lovelace:" in text and "dashboards:" in text:
            if re.search(r"filename:\s*dashboards/empire_main\.yaml\s*$", text, re.M):
                text = re.sub(
                    r"(filename:\s*dashboards/empire_main\.yaml\s*\n)",
                    r"\1" + wall_block,
                    text,
                    count=1,
                )
            else:
                text = re.sub(
                    r"(filename:\s*dashboards/[^\n]+\n)",
                    r"\1" + wall_block,
                    text,
                    count=1,
                )
        else:
            text = text.rstrip() + """
lovelace:
  mode: storage
  dashboards:
    empire-wall:
      mode: yaml
      title: Панель
      icon: mdi:tablet-dashboard
      show_in_sidebar: true
      require_admin: false
      filename: dashboards/empire_wall.yaml
"""
        changed = True
        print("  + lovelace empire-wall")

if changed:
    cfg.write_text(text)
    print("  configuration.yaml обновлён")
else:
    print("  configuration.yaml уже содержит themes + empire-wall")
PY

scp -q ${SCP_OPTS} "${TMP_CFG}" "${SSH_TARGET}:${HA_CONFIG}/configuration.yaml"

echo "==> Перезапуск HA core"
ssh ${SSH_OPTS} -p "${HA_SSH_PORT}" "${SSH_TARGET}" "ha core restart" || \
  ssh ${SSH_OPTS} -p "${HA_SSH_PORT}" "${SSH_TARGET}" "docker restart homeassistant 2>/dev/null || true"

echo "==> Ezviz (если creds в /config/secrets.yaml)"
PYTHON="${EMPIRE_DIR}/venv/bin/python3"
[[ -x "${PYTHON}" ]] || PYTHON=python3
if [[ -f "${EMPIRE_DIR}/.env" ]]; then set -a && source "${EMPIRE_DIR}/.env" && set +a; fi
scp -q ${SCP_OPTS} "${SSH_TARGET}:${HA_CONFIG}/secrets.yaml" /tmp/ha_secrets_ezviz.yaml 2>/dev/null || true
HA_SECRETS=/tmp/ha_secrets_ezviz.yaml "${PYTHON}" "${EMPIRE_DIR}/tools/ha_ezviz_setup.py" || true

echo ""
echo "Готово. Откройте:"
echo "  http://${HA_HOST}:8123/empire-wall/dom"
echo ""
echo "Дальше (если камеры ещё не видны):"
echo "  1. Добавьте в /config/secrets.yaml: ezviz_username, ezviz_password, ezviz_url"
echo "  2. bash deploy/ha_deploy_wall_dashboard.sh  (или python3 tools/ha_ezviz_setup.py)"
echo "  3. Планшет: Fully Kiosk / HA Companion → kiosk mode, тема empire_wall"
echo "  Подробно: docs/HA_EZVIZ_WALL_DASHBOARD.md"
