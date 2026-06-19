#!/usr/bin/env bash
# Синхронизация Garmin (через Intervals.icu) → health.db
#
# Нужно в .env:
#   INTERVALS_ICU_API_KEY=...
#   INTERVALS_ICU_ATHLETE_ID=i615695
#
# Cron (пример, каждый час):
#   5 * * * * /root/projects/empire/scripts/intervals_sync.sh >> /var/log/empire-intervals-sync.log 2>&1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/venv/bin/python3" ]]; then
  PY="$ROOT/venv/bin/python3"
else
  PY=python3
fi

"$PY" "$ROOT/intervals_sync.py"
