#!/bin/sh
# DEPRECATED: все ИИ (в т.ч. Gemini/Cursor) → awg0. См. 36-ai-via-amnezia.sh
# Старое: Gemini → VLESS google_ai, OpenAI/Claude → awg0.
set -eu
BASE="${FLINT2_BASE:-http://193.233.232.48:8789}"
log() { printf '\033[1;32m[gemini]\033[0m %s\n' "$*"; }
log "перенаправляю на 36-ai-via-amnezia.sh (все ИИ → Amnezia awg0)"
curl -fsSL "$BASE/36-ai-via-amnezia.sh" | sh
