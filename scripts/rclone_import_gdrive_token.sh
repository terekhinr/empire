#!/usr/bin/env bash
# Import Google Drive token (if you ran rclone authorize on Windows).
# On Windows PowerShell:
#   rclone authorize "drive" --drive-scope drive.readonly
# Copy the JSON line it prints, save as token.json, upload to VPS, then:
#   sudo bash scripts/rclone_import_gdrive_token.sh /root/token.json
set -euo pipefail

CONF="${RCLONE_CONFIG:-/root/.config/rclone/rclone.conf}"
TOKEN_FILE="${1:-}"

if [[ -z "$TOKEN_FILE" || ! -f "$TOKEN_FILE" ]]; then
  echo "Usage: sudo bash $0 /path/to/token.json" >&2
  echo "token.json = one line JSON from: rclone authorize drive" >&2
  exit 1
fi

if ! rclone listremotes 2>/dev/null | grep -q '^gdrive:$'; then
  rclone config create gdrive drive scope drive.readonly config_is_local=false
fi

TOKEN="$(tr -d '\n' < "$TOKEN_FILE")"
rclone config update gdrive token "$TOKEN" --config "$CONF"
chmod 600 "$CONF"

echo "Test:"
rclone lsd "gdrive:Easy Voice Recorder"
echo "OK. Run: sudo systemctl enable --now voice-pipeline.timer"
