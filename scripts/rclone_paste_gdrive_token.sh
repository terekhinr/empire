#!/usr/bin/env bash
# Paste Google token JSON into a file, then import (after rclone authorize on Windows).
set -euo pipefail

CONF="${RCLONE_CONFIG:-/root/.config/rclone/rclone.conf}"
TOKEN_FILE="${1:-/root/gdrive_token.json}"

echo "=== Import Google Drive token for rclone ==="
echo ""
echo "1) On Windows run:"
echo '     rclone authorize "drive" --drive-scope drive.readonly'
echo ""
echo "2) Copy ONLY the JSON line (starts with { ends with })"
echo "   WITHOUT text 'Paste the following' or arrows."
echo ""
echo "3) On VPS, save JSON to: $TOKEN_FILE"
echo "   Example: nano $TOKEN_FILE"
echo "   (paste one line, Ctrl+O, Enter, Ctrl+X)"
echo ""
read -r -p "Press Enter when $TOKEN_FILE is saved..."

if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "File not found: $TOKEN_FILE" >&2
  exit 1
fi

TOKEN="$(tr -d '\n\r' < "$TOKEN_FILE")"
if [[ "$TOKEN" != \{* ]]; then
  echo "File must be JSON starting with { — you may have copied extra text." >&2
  exit 1
fi

if ! rclone listremotes 2>/dev/null | grep -q '^gdrive:$'; then
  rclone config create gdrive drive scope drive.readonly config_is_local=false
fi

rclone config update gdrive token "$TOKEN" --config "$CONF"
chmod 600 "$CONF"

echo ""
echo "Test:"
rclone lsd "gdrive:Easy Voice Recorder"
echo ""
echo "OK. Next:"
echo "  sudo systemctl start voice-pipeline.service"
echo "  sudo systemctl enable --now voice-pipeline.timer"
rm -f "$TOKEN_FILE"
