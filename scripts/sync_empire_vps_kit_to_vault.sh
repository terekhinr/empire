#!/bin/bash
# Копирует PC-скрипты Tailscale в Obsidian vault и (опционально) пушит на Яндекс.Диск.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/templates/obsidian_life_kit/empire-vps"
DST="$ROOT/data/obsidian_vault/Life/tools/empire-vps"
PUSH="${1:-}"

mkdir -p "$DST"
cp -a "$SRC"/. "$DST"/
# всегда свежие ps1 из scripts/
cp "$ROOT/scripts/cursor_vps_tailscale_setup_pc.ps1" "$DST/"
cp "$ROOT/scripts/cursor_vps_tailscale_rollback_pc.ps1" "$DST/"
echo "OK: $DST"

if [[ "$PUSH" == "--push" ]]; then
  bash "$ROOT/scripts/obsidian_rclone_push_vault.sh"
fi
