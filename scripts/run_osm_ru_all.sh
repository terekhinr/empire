#!/usr/bin/env bash
# OSM-парсинг бань: вся РФ из реестра (EUROPE_RU + Урал + Сибирь + ДВ).
# Пишет только status=draft — live-карта / published не затрагиваются.
# Лог: logs/osm_ru_all.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs

REGIONS_SET="${1:-RU_ALL}"
SLEEP="${BANYA_OSM_SLEEP:-12}"
LOG="${ROOT}/logs/osm_ru_all.log"

echo "=== $(date -Is) OSM ${REGIONS_SET} start (sleep=${SLEEP}s) ===" | tee -a "$LOG"

./venv/bin/python tools/banya_schema_mvp.py | tee -a "$LOG"

PYTHONUNBUFFERED=1 ./venv/bin/python tools/parsers/osm_banyas.py \
  --regions "$REGIONS_SET" \
  --sleep "$SLEEP" \
  2>&1 | tee -a "$LOG"

echo "=== $(date -Is) OSM ${REGIONS_SET} done ===" | tee -a "$LOG"
