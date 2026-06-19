#!/usr/bin/env bash
# Установка таймеров Obsidian sync + VPS backup (после настройки /etc/empire/rclone.env).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

chmod +x "$ROOT/scripts/"*.sh 2>/dev/null || true

apt-get install -y rclone >/dev/null 2>&1 || true

mkdir -p /etc/empire
if [[ ! -f /etc/empire/rclone.env ]]; then
  cp "$ROOT/deploy/rclone.env.example" /etc/empire/rclone.env
  chmod 600 /etc/empire/rclone.env
  echo "Создан /etc/empire/rclone.env — вставьте логин и пароль приложения Яндекса."
fi

if ! grep -q OBSIDIAN_EMPIRE_INCOMING /etc/empire/empire.env 2>/dev/null; then
  mkdir -p /etc/empire
  cat >> /etc/empire/empire.env <<'EOF'

# Obsidian вариант A (все каналы, все queue/)
OBSIDIAN_EMPIRE_INCOMING=/root/projects/empire/data/obsidian_vault/Empire
EOF
  chmod 600 /etc/empire/empire.env 2>/dev/null || true
  echo "Добавлен OBSIDIAN_EMPIRE_INCOMING в /etc/empire/empire.env"
fi

for unit in obsidian-rclone-sync obsidian-rclone-push empire-vps-backup-yandex voice-pipeline; do
  cp "$ROOT/deploy/${unit}.service" /etc/systemd/system/
  [[ -f "$ROOT/deploy/${unit}.timer" ]] && cp "$ROOT/deploy/${unit}.timer" /etc/systemd/system/
done

if [[ ! -f /etc/empire/voice.env ]]; then
  cp "$ROOT/deploy/voice.env.example" /etc/empire/voice.env
  chmod 600 /etc/empire/voice.env
  echo "Создан /etc/empire/voice.env"
fi

systemctl daemon-reload

if rclone listremotes 2>/dev/null | grep -q '^yandex:$'; then
  systemctl enable --now obsidian-rclone-sync.timer empire-vps-backup-yandex.timer
  systemctl start obsidian-rclone-sync.service || true
  echo "Таймеры включены: obsidian-rclone-sync, empire-vps-backup-yandex"
  if rclone listremotes 2>/dev/null | grep -q '^gdrive:$' && \
     rclone lsd "gdrive:Easy Voice Recorder" &>/dev/null; then
    systemctl enable --now voice-pipeline.timer
    echo "Таймер voice-pipeline включён (Google → Whisper → Life/)"
  else
    echo "Голос: после OAuth Google выполните:"
    echo "  sudo bash $ROOT/scripts/rclone_connect_gdrive_oauth.sh"
    echo "  sudo systemctl enable --now voice-pipeline.timer"
  fi
  echo "Перезапуск бота: systemctl restart empire_main"
else
  echo "Remote yandex ещё нет. Шаги:"
  echo "  1) Пароль приложения: https://id.yandex.ru/security/app-passwords"
  echo "  2) Заполните /etc/empire/rclone.env"
  echo "  3) sudo bash $ROOT/scripts/rclone_setup_yandex_webdav.sh"
  echo "  4) sudo bash $ROOT/scripts/install_rclone_empire.sh"
fi
