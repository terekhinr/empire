#!/bin/sh
# СТАБИЛЬНЫЙ YouTube + интернет: SKeen (Google→VPS), остальное direct. nfqws2 OFF.
# Рекомендуется: curl -fsSL http://193.233.232.48:8787/36-final-stable-youtube.sh | sh
# Этот скрипт — обёртка для совместимости.
set -eu
export PATH="/opt/bin:/opt/sbin:$PATH"
BASE="${KEENETIC_XKEEN_BASE:-http://193.233.232.48:8787}"
exec curl -fsSL "$BASE/36-final-stable-youtube.sh" | sh
