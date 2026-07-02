#!/usr/bin/env bash
# Re-transcribe recent notes (medium) and push to Yandex. Long-running — use tmux/nohup.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${VOICE_RETRANSCRIBE_LOG:-$ROOT/data/voice_retranscribe.log}"
SINCE="${1:-2026-06-23}"

ENV_FILE="${VOICE_ENV_FILE:-/etc/empire/voice.env}"
RCLONE_ENV="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"
[[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a
[[ -f "$RCLONE_ENV" ]] && set -a && source "$RCLONE_ENV" && set +a

export PYTHONUNBUFFERED=1

{
  echo "=== $(date -Iseconds) retranscribe since $SINCE ==="
  cd "$ROOT/scripts"
  "$ROOT/venv/bin/python" voice_retranscribe_notes.py --since "$SINCE"
  echo "=== $(date -Iseconds) push pipeline ==="
  bash "$ROOT/scripts/voice_vps_pipeline.sh"
  echo "=== $(date -Iseconds) DONE ==="
} >>"$LOG" 2>&1
