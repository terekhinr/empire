#!/usr/bin/env bash
# Скачать последний релиз geminese в templates/obsidian_plugins/geminese/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/templates/obsidian_plugins/geminese"
VER="${GEMINESE_VERSION:-0.9.1}"
BASE="https://github.com/Momoyu404/geminese/releases/download/${VER}"
mkdir -p "$DEST"
for f in main.js manifest.json styles.css; do
  curl -fsSL -o "$DEST/$f" "$BASE/$f"
  echo "ok: $f"
done
echo "Geminese $VER -> $DEST"
