#!/usr/bin/env bash
# Залп отзывов по списку spot id (по одной бане, пауза против капчи).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${ROOT}/logs/banya_bulk_scrape.log"
MAX_PER_SPOT="${1:-10}"
PAUSE="${2:-8}"
IDS="${3:-}"

mkdir -p "${ROOT}/logs"
exec > >(tee -a "$LOG") 2>&1

echo "=== bulk scrape start $(date -Iseconds) max=$MAX_PER_SPOT pause=$PAUSE ==="

if [[ -z "$IDS" ]]; then
  IDS=$(./venv/bin/python - <<'PY'
import sqlite3
c=sqlite3.connect("empire.db")
q="""
SELECT s.id FROM banya_spots s
WHERE s.status='published'
  AND s.yandex_url IS NOT NULL AND trim(s.yandex_url)!=''
ORDER BY (
  SELECT COUNT(*) FROM banya_reviews r
  WHERE r.spot_id=s.id AND r.status='approved'
) ASC, s.rating_avg DESC NULLS LAST, s.id
LIMIT 30
"""
print(" ".join(str(r[0]) for r in c.execute(q)))
PY
)
fi

total_saved=0
total_miss=0
for sid in $IDS; do
  echo "--- spot $sid ---"
  if out=$(./venv/bin/python tools/parsers/yandex_scrape.py reviews --id "$sid" --max "$MAX_PER_SPOT" 2>&1); then
    echo "$out" | tail -3
    if echo "$out" | grep -q 'saved='; then
      s=$(echo "$out" | grep 'reviews done' | sed -n 's/.*saved=\([0-9]*\).*/\1/p')
      m=$(echo "$out" | grep 'reviews done' | sed -n 's/.*miss=\([0-9]*\).*/\1/p')
      total_saved=$((total_saved + ${s:-0}))
      total_miss=$((total_miss + ${m:-0}))
    fi
  else
    echo "FAIL spot $sid"
    total_miss=$((total_miss + 1))
  fi
  sleep "$PAUSE"
done

echo "=== bulk scrape done $(date -Iseconds) total_saved~$total_saved miss_spots~$total_miss ==="
