#!/usr/bin/env bash
# Еженедельный лёгкий прогон FLAGSHIP (R7): без OSM-массовости, низкий nice/ionice.
# Отчёт — в empire-weekly-report / logs/banya_weekly.log. Не чаще 1×/нед.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/root/.cache/ms-playwright}"
export PLAYWRIGHT_HOST_PLATFORM_OVERRIDE="${PLAYWRIGHT_HOST_PLATFORM_OVERRIDE:-ubuntu24.04-x64}"
export PYTHONUNBUFFERED=1
export BANYA_MIN_REVIEWS="${BANYA_MIN_REVIEWS:-50}"
export BANYA_MIN_RATING="${BANYA_MIN_RATING:-4.0}"
export BANYA_REVIEW_MAX_AGE_DAYS="${BANYA_REVIEW_MAX_AGE_DAYS:-365}"
export BANYA_SPOT_STALE_DAYS="${BANYA_SPOT_STALE_DAYS:-270}"
export BANYA_REQUIRE_PHONE="${BANYA_REQUIRE_PHONE:-1}"
export BANYA_FLAGSHIP_SKIP_OSM=1
export BANYA_FLAGSHIP_SKIP_REVIEWS="${BANYA_FLAGSHIP_SKIP_REVIEWS:-0}"
export BANYA_FLAGSHIP_ENRICH_LIMIT="${BANYA_FLAGSHIP_ENRICH_LIMIT:-20}"
export BANYA_FLAGSHIP_REVIEWS_BATCH="${BANYA_FLAGSHIP_REVIEWS_BATCH:-6}"
export BANYA_FLAGSHIP_REVIEWS_MAX="${BANYA_FLAGSHIP_REVIEWS_MAX:-5}"
export BANYA_REFRESH_LIMIT="${BANYA_REFRESH_LIMIT:-25}"
# Паузы между точками — бережнее к 2 vCPU / 4GB
export BANYA_REFRESH_WAIT_MIN="${BANYA_REFRESH_WAIT_MIN:-14}"
export BANYA_REFRESH_WAIT_MAX="${BANYA_REFRESH_WAIT_MAX:-22}"

LOG="${ROOT}/logs/banya_weekly.log"
mkdir -p logs
REGIONS="${BANYA_FLAGSHIP_REGIONS:-MSK,MO,SPB,LO}"
STAMP="$(date -Iseconds)"

{
  echo "=== BANYA WEEKLY START $STAMP ==="
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg) mem_avail=$(awk '/MemAvailable/{print $2}' /proc/meminfo)k"

  # Не стартовать, если уже крутится scrape (защита от наложений)
  if pgrep -f "tools/parsers/yandex_scrape.py" >/dev/null 2>&1; then
    echo "SKIP: yandex_scrape already running"
    exit 0
  fi

  IFS=',' read -ra RARR <<< "$REGIONS"
  for reg in "${RARR[@]}"; do
    echo "--- refresh $reg limit=$BANYA_REFRESH_LIMIT ---"
    nice -n 15 ionice -c3 ./venv/bin/python tools/parsers/yandex_scrape.py \
      refresh --region "$reg" --limit "$BANYA_REFRESH_LIMIT" || true
    sleep 5
  done

  echo "--- quality gate ---"
  ./venv/bin/python tools/banya_quality.py --apply || true

  echo "--- enrich+reviews (flagship, small) ---"
  nice -n 15 ionice -c3 ./scripts/run_flagship_banya.sh || true

  echo "--- quality gate final ---"
  ./venv/bin/python tools/banya_quality.py --apply || true

  ./venv/bin/python scripts/empire_gdepar_parse_summary.py || true
  echo "=== BANYA WEEKLY DONE $(date -Iseconds) ==="
} 2>&1 | tee -a "$LOG"
