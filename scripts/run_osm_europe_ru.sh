#!/usr/bin/env bash
# OSM-парсинг бань: европейская часть РФ до Урала.
# Лог: logs/osm_europe_ru.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs

echo "=== $(date -Is) OSM EUROPE_RU start ===" | tee -a logs/osm_europe_ru.log

./venv/bin/python tools/banya_schema_mvp.py | tee -a logs/osm_europe_ru.log

PYTHONUNBUFFERED=1 ./venv/bin/python tools/parsers/osm_banyas.py --regions EUROPE_RU 2>&1 | tee -a logs/osm_europe_ru.log

echo "=== $(date -Is) OSM EUROPE_RU done ===" | tee -a logs/osm_europe_ru.log
