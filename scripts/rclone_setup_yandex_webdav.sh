#!/usr/bin/env bash
# Один remote «yandex» через WebDAV (без OAuth в браузере на VPS).
# Пароль приложения: https://id.yandex.ru/security/app-passwords → «Пароли приложений» → rclone/VPS
set -euo pipefail

CONF="${RCLONE_CONFIG:-/root/.config/rclone/rclone.conf}"
ENV_FILE="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

USER="${YANDEX_DISK_USER:-}"
PASS="${YANDEX_DISK_APP_PASSWORD:-}"

if [[ -z "$USER" || -z "$PASS" ]]; then
  echo "Задайте в $ENV_FILE:" >&2
  echo '  YANDEX_DISK_USER="ваш@email.ru"' >&2
  echo '  YANDEX_DISK_APP_PASSWORD="пароль_приложения"' >&2
  echo "Затем: sudo bash $0" >&2
  exit 1
fi

mkdir -p "$(dirname "$CONF")"
if rclone listremotes 2>/dev/null | grep -q '^yandex:$'; then
  echo "Remote yandex уже есть — удалите вручную или: rclone config delete yandex"
  exit 1
fi

rclone config create yandex webdav \
  url "https://webdav.yandex.ru" \
  vendor other \
  user "$USER" \
  pass "$PASS"

echo "OK remote yandex"
echo "Проверка:"
rclone lsd yandex: | head -20
