#!/usr/bin/env bash
# Create Obsidian vault folders for voice routing + local staging mirror.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VAULT="${OBSIDIAN_VAULT_ROOT:-$ROOT/data/obsidian_vault}"
STAGING="${VAULT_STAGING:-$ROOT/data/voice_vault_staging}"

PATHS=(
  "Life/inbox"
  "Life/voice/transcribed"
  "Life/voice/raw"
  "Life/voice/processed"
  "Empire/pension/inbox"
  "База знаний/Книги/На-пенсию-никогда/заметки"
  "База знаний/Книги/Трупик-майора/заметки"
  "Контент/Статьи/заметки-voice"
  "Входящие"
)

for base in "$VAULT" "$STAGING"; do
  for rel in "${PATHS[@]}"; do
    mkdir -p "$base/$rel"
  done
done

echo "Vault:   $VAULT"
echo "Staging: $STAGING"
echo "Folders ready. Push vault once:"
echo "  sudo bash $ROOT/scripts/obsidian_rclone_push_vault.sh"
