#!/usr/bin/env bash
# Voice pipeline: audio -> Whisper -> routed Obsidian notes -> Yandex Disk
#
# VOICE_SOURCE=yandex (default, простой путь):
#   ПК: Google Drive Desktop -> sync_evrec_to_life.ps1 -> Life/voice/raw на Яндекс.Диске
#   VPS: pull raw с Яндекса -> whisper -> push .md
#
# VOICE_SOURCE=gdrive (сложный, OAuth на VPS):
#   pull Easy Voice Recorder с Google Drive
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${VOICE_ENV_FILE:-/etc/empire/voice.env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi
RCLONE_ENV="${RCLONE_ENV_FILE:-/etc/empire/rclone.env}"
[[ -f "$RCLONE_ENV" ]] && source "$RCLONE_ENV"

VOICE_SOURCE="${VOICE_SOURCE:-yandex}"
GDRIVE_REMOTE="${VOICE_GDRIVE_REMOTE:-gdrive}"
GDRIVE_PATH="${VOICE_GDRIVE_PATH:-Easy Voice Recorder}"
YANDEX_REMOTE="${RCLONE_REMOTE:-yandex}"
YANDEX_VAULT="${YANDEX_VAULT_PATH:-obsidian (2)}"
YANDEX_RAW="${YANDEX_VOICE_RAW:-${YANDEX_VAULT}/Life/voice/raw}"

INCOMING="${VOICE_INCOMING:-$ROOT/data/voice_incoming}"
STAGING="${VAULT_STAGING:-$ROOT/data/voice_vault_staging}"
VENV_PY="${VOICE_VENV_PY:-$ROOT/venv/bin/python}"
ROUTE_CONFIG="${VOICE_ROUTE_CONFIG:-$ROOT/data/voice_route_config.json}"

mkdir -p "$INCOMING" "$STAGING/Life/voice/transcribed"

if ! command -v rclone >/dev/null 2>&1; then
  echo "rclone missing" >&2
  exit 1
fi

if [[ "$VOICE_SOURCE" == "gdrive" ]]; then
  if ! rclone listremotes 2>/dev/null | grep -q "^${GDRIVE_REMOTE}:$"; then
    echo "Remote ${GDRIVE_REMOTE} not configured." >&2
    exit 1
  fi
  echo "== Pull audio from Google Drive =="
  if ! rclone copy "${GDRIVE_REMOTE}:${GDRIVE_PATH}" "$INCOMING" \
    --fast-list \
    --ignore-existing \
    --transfers 2 \
    --timeout 10m \
    --include "*.mp3" \
    --include "*.m4a" \
    --include "*.aac" \
    --include "*.wav" \
    -v; then
    echo "WARN: Google Drive pull failed." >&2
    exit 1
  fi
else
  echo "== Pull audio from Yandex (Life/voice/raw) =="
  # --ignore-existing: не висеть на повторной закачке тех же mp3
  rclone copy "${YANDEX_REMOTE}:${YANDEX_RAW}" "$INCOMING" \
    --fast-list \
    --ignore-existing \
    --transfers 2 \
    --timeout 10m \
    --include "*.mp3" \
    --include "*.m4a" \
    --include "*.aac" \
    --include "*.wav" \
    -v
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "Python venv not found: $VENV_PY" >&2
  exit 1
fi

if ! "$VENV_PY" -c "import faster_whisper" 2>/dev/null; then
  echo "Install: $ROOT/venv/bin/pip install faster-whisper" >&2
  exit 1
fi

export VOICE_INCOMING="$INCOMING"
export VAULT_STAGING="$STAGING"
export VOICE_ROUTE_CONFIG="$ROUTE_CONFIG"

echo "== Transcribe + route =="
cd "$ROOT/scripts"
"$VENV_PY" voice_vps_transcribe.py

echo "== Push notes to Yandex Disk =="
if [[ ! -f "$ROUTE_CONFIG" ]]; then
  echo "Missing $ROUTE_CONFIG" >&2
  exit 1
fi

mapfile -t PUSH_PATHS < <("$VENV_PY" -c "
import json
from pathlib import Path
cfg = json.loads(Path('$ROUTE_CONFIG').read_text(encoding='utf-8'))
for p in cfg.get('push_paths', []):
    print(p)
")

for rel in "${PUSH_PATHS[@]}"; do
  local_dir="$STAGING/$rel"
  if [[ -d "$local_dir" ]] && compgen -G "$local_dir/"* >/dev/null 2>&1; then
    echo "  copy -> ${YANDEX_VAULT}/${rel}"
    rclone copy "$local_dir" "${YANDEX_REMOTE}:${YANDEX_VAULT}/${rel}" -v --ignore-checksum
  fi
done

echo "Done. Obsidian on PC gets files via Yandex Disk sync."
