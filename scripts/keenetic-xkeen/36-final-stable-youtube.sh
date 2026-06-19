#!/bin/sh
# Обёртка → 37-optimize-youtube-vps.sh (обратная совместимость)
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
exec curl -fsSL "$BASE/37-optimize-youtube-vps.sh" | sh
