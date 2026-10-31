#!/usr/bin/env bash
# Приоритет R7: только MSK + MO + SPB + LO.
# OSM (draft) → enrich телефонов → (опц.) отзывы. Без mass-pubauto Сибири.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/root/.cache/ms-playwright}"
export PLAYWRIGHT_HOST_PLATFORM_OVERRIDE="${PLAYWRIGHT_HOST_PLATFORM_OVERRIDE:-ubuntu24.04-x64}"
export PYTHONUNBUFFERED=1
# R7 quality: только живые бани с трафиком и телефоном
export BANYA_MIN_REVIEWS="${BANYA_MIN_REVIEWS:-50}"
export BANYA_MIN_RATING="${BANYA_MIN_RATING:-4.0}"
export BANYA_REVIEW_MAX_AGE_DAYS="${BANYA_REVIEW_MAX_AGE_DAYS:-365}"
export BANYA_SPOT_STALE_DAYS="${BANYA_SPOT_STALE_DAYS:-270}"
export BANYA_REQUIRE_PHONE="${BANYA_REQUIRE_PHONE:-1}"
LOG="${ROOT}/logs/banya_flagship.log"
mkdir -p logs

REGIONS="${BANYA_FLAGSHIP_REGIONS:-MSK,MO,SPB,LO}"
ENRICH_LIMIT="${BANYA_FLAGSHIP_ENRICH_LIMIT:-80}"
SKIP_OSM="${BANYA_FLAGSHIP_SKIP_OSM:-0}"
SKIP_ENRICH="${BANYA_FLAGSHIP_SKIP_ENRICH:-0}"
SKIP_REVIEWS="${BANYA_FLAGSHIP_SKIP_REVIEWS:-1}"
REVIEWS_BATCH="${BANYA_FLAGSHIP_REVIEWS_BATCH:-15}"
REVIEWS_MAX="${BANYA_FLAGSHIP_REVIEWS_MAX:-8}"

{
  echo "=== FLAGSHIP $(date -Iseconds) regions=$REGIONS ==="

  if [[ "$SKIP_OSM" != "1" ]]; then
    echo "--- OSM FLAGSHIP ---"
    ./venv/bin/python tools/parsers/osm_banyas.py --regions FLAGSHIP || true
  else
    echo "--- OSM skip ---"
  fi

  if [[ "$SKIP_ENRICH" != "1" ]]; then
    IFS=',' read -ra RARR <<< "$REGIONS"
    for reg in "${RARR[@]}"; do
      echo "--- enrich $reg limit=$ENRICH_LIMIT ---"
      ./venv/bin/python tools/parsers/yandex_scrape.py enrich --region "$reg" --limit "$ENRICH_LIMIT" || true
      sleep 4
    done
  else
    echo "--- enrich skip ---"
  fi

  if [[ "$SKIP_REVIEWS" != "1" ]]; then
    IFS=',' read -ra RARR <<< "$REGIONS"
    for reg in "${RARR[@]}"; do
      echo "--- reviews $reg batch=$REVIEWS_BATCH ---"
      ./venv/bin/python tools/parsers/yandex_scrape.py reviews --status published --region "$reg" --batch "$REVIEWS_BATCH" --max "$REVIEWS_MAX" || true
      sleep 4
    done
  else
    echo "--- reviews skip (set BANYA_FLAGSHIP_SKIP_REVIEWS=0 to enable) ---"
  fi

  echo "--- hide offtopic FLAGSHIP (dry then apply) ---"
  ./venv/bin/python tools/banya_hide_offtopic.py --show --region "$REGIONS" || true
  ./venv/bin/python tools/banya_hide_offtopic.py --apply --region "$REGIONS" || true

  echo "=== FLAGSHIP DONE $(date -Iseconds) ==="
} 2>&1 | tee -a "$LOG"
