#!/usr/bin/env bash
# Print Google OAuth URL for voice pipeline (paste code via rclone_connect_gdrive_oauth.sh).
set -euo pipefail
CONF="${RCLONE_CONFIG:-/root/.config/rclone/rclone.conf}"
if ! rclone listremotes 2>/dev/null | grep -q '^gdrive:$'; then
  rclone config create gdrive drive scope drive.readonly config_is_local=false
fi
echo "Open URL, allow access, then run: sudo bash scripts/rclone_connect_gdrive_oauth.sh"
rclone authorize "drive" --auth-no-open-browser --drive-scope drive.readonly
