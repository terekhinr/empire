#!/usr/bin/env bash
# Одноразовый quality-прогон FLAGSHIP (R7):
#   refresh метрик → demote балласта → enrich/reviews → demote снова.
# Не гонять demote до refresh: иначе точки с reviews_total=0 уйдут в draft ошибочно
# (после бага COUNT) или останутся без шанса обновить счётчик Яндекса.
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
export BANYA_FLAGSHIP_SKIP_OSM="${BANYA_FLAGSHIP_SKIP_OSM:-1}"
export BANYA_FLAGSHIP_SKIP_REVIEWS="${BANYA_FLAGSHIP_SKIP_REVIEWS:-0}"
export BANYA_FLAGSHIP_ENRICH_LIMIT="${BANYA_FLAGSHIP_ENRICH_LIMIT:-40}"
export BANYA_FLAGSHIP_REVIEWS_BATCH="${BANYA_FLAGSHIP_REVIEWS_BATCH:-10}"
export BANYA_FLAGSHIP_REVIEWS_MAX="${BANYA_FLAGSHIP_REVIEWS_MAX:-8}"

LOG=logs/banya_flagship_nohup.out
mkdir -p logs
REGIONS="${BANYA_FLAGSHIP_REGIONS:-MSK,MO,SPB,LO}"
REFRESH_LIMIT="${BANYA_REFRESH_LIMIT:-60}"

{
  echo "=== QUALITY WRAPPER START $(date -Iseconds) ==="
  echo "thresholds: min_rev=$BANYA_MIN_REVIEWS min_★=$BANYA_MIN_RATING review_age≤${BANYA_REVIEW_MAX_AGE_DAYS}d stale≤${BANYA_SPOT_STALE_DAYS}d phone=$BANYA_REQUIRE_PHONE"

  IFS=',' read -ra RARR <<< "$REGIONS"
  for reg in "${RARR[@]}"; do
    echo "--- refresh $reg limit=$REFRESH_LIMIT ---"
    ./venv/bin/python tools/parsers/yandex_scrape.py refresh --region "$reg" --limit "$REFRESH_LIMIT" || true
    sleep 3
  done

  echo "--- quality gate after refresh ---"
  ./venv/bin/python tools/banya_quality.py --show || true
  ./venv/bin/python tools/banya_quality.py --apply || true

  ./scripts/run_flagship_banya.sh

  echo "--- quality gate after enrich/reviews ---"
  ./venv/bin/python tools/banya_quality.py --apply || true

  echo "=== QUALITY WRAPPER DONE $(date -Iseconds) ==="
} 2>&1 | tee -a "$LOG"
