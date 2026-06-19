#!/usr/bin/env bash
# Google Drive remote for voice pipeline (one-time OAuth).
# On VPS (SSH): sudo bash scripts/rclone_setup_gdrive.sh
# You will get a URL — open on phone/PC, allow access, paste the code back into SSH.
set -euo pipefail

if rclone listremotes 2>/dev/null | grep -q '^gdrive:$'; then
  echo "Remote gdrive already exists."
  rclone lsd "gdrive:Easy Voice Recorder" 2>/dev/null | head -5 || \
    rclone lsd gdrive: | head -10
  exit 0
fi

echo "=== Google Drive OAuth (read-only enough for voice pull) ==="
echo "When prompted, open the URL in a browser, log in to the Google account"
echo "that owns Easy Voice Recorder backups."
echo ""

rclone config create gdrive drive scope drive.readonly config_is_local=false

echo ""
echo "Test:"
rclone lsd "gdrive:Easy Voice Recorder" || {
  echo "If folder name differs, list roots:"
  rclone lsd gdrive: | head -20
}
echo "OK. Run: sudo bash scripts/voice_vps_pipeline.sh"
