#!/usr/bin/env bash
# Google Drive OAuth on headless VPS.
# rclone opens http://127.0.0.1:PORT/... — works only via port-forward to your PC, NOT on phone.
#
# Usage: sudo bash scripts/rclone_connect_gdrive_oauth.sh
set -euo pipefail

CONF="${RCLONE_CONFIG:-/root/.config/rclone/rclone.conf}"

if ! rclone listremotes 2>/dev/null | grep -q '^gdrive:$'; then
  rclone config create gdrive drive scope drive.readonly config_is_local=false
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ВАЖНО: ссылка будет http://127.0.0.1:XXXX — это НЕ для телефона ║"
echo "║  Открывать на ПК, когда проброшен порт (см. ниже).               ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Перед Enter:"
echo "  Cursor → вкладка PORTS (Порты) → Forward port → введите порт из ссылки ниже"
echo "  (число после 127.0.0.1:, например 53682)"
echo ""
echo "Или в Windows PowerShell (второе окно, не закрывать):"
echo "  ssh -L 53682:127.0.0.1:53682 root@ВАШ_VPS"
echo ""
read -r -p "Нажмите Enter, когда готовы открыть ссылку на ПК… "

echo ""
echo "=== Скопируйте ссылку 127.0.0.1 ниже → откройте в Chrome на ПК ==="
echo "=== Google-аккаунт: тот же, что Easy Voice Recorder ==="
echo ""

# Зависший rclone authorize держит 127.0.0.1:53682 → bind: address already in use
pkill -f 'rclone authorize' 2>/dev/null || true
sleep 1

RAW="$(rclone authorize "drive" --auth-no-open-browser --drive-scope drive.readonly)"
TOKEN="$(printf '%s' "$RAW" | grep -oE '\{.*\}' | head -1)"
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: no JSON token in rclone authorize output" >&2
  exit 1
fi
rclone config update gdrive token "$TOKEN" --config "$CONF"
chmod 600 "$CONF"

echo ""
echo "Test:"
if ! rclone lsd "gdrive:Easy Voice Recorder" >/dev/null 2>&1; then
  echo "ERROR: папка 'Easy Voice Recorder' не найдена на этом Google-аккаунте." >&2
  echo "Войдите в тот же аккаунт, куда Easy Voice Recorder кладёт записи с телефона." >&2
  exit 1
fi
rclone lsd "gdrive:Easy Voice Recorder"
echo ""
echo "OK. Запуск пайплайна:"
echo "  sudo systemctl start voice-pipeline.service"
