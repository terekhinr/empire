#!/usr/bin/env bash
# Форсированный парсинг отзывов (yandex.com URL) + публикация на сайте.
# Регионы: env BANYA_FORCE_REGIONS (по умолчанию GDEPAR = ЦФО + SPB + LO).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/root/.cache/ms-playwright}"
export PYTHONUNBUFFERED=1
LOG="${ROOT}/logs/banya_bulk_scrape.log"
MAX="${1:-12}"
PAUSE="${2:-10}"
SPOT_LIMIT="${BANYA_FORCE_SPOT_LIMIT:-60}"
REGIONS="${BANYA_FORCE_REGIONS:-GDEPAR}"

mkdir -p logs
exec >>"$LOG" 2>&1

echo "=== FORCE PIPELINE $(date -Iseconds) max=$MAX pause=$PAUSE regions=$REGIONS limit=$SPOT_LIMIT ==="

IDS=$(BANYA_FORCE_REGIONS="$REGIONS" BANYA_FORCE_SPOT_LIMIT="$SPOT_LIMIT" ./venv/bin/python - <<'PY'
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
sys.path.insert(0, str(ROOT))
from tools.banya_regions import expand_region_tokens, GDEPAR_REVIEW_REGIONS

regions = expand_region_tokens(
    [r.strip() for r in os.environ.get("BANYA_FORCE_REGIONS", "GDEPAR").split(",") if r.strip()]
) or list(GDEPAR_REVIEW_REGIONS)
limit = int(os.environ.get("BANYA_FORCE_SPOT_LIMIT", "60"))
ph = ",".join("?" * len(regions))
c = sqlite3.connect("empire.db")
q = f"""
SELECT s.id FROM banya_spots s
WHERE s.status='published'
  AND s.region IN ({ph})
  AND s.yandex_url LIKE '%yandex.com/maps%'
ORDER BY (
  SELECT COUNT(*) FROM banya_reviews r
  WHERE r.spot_id=s.id AND r.status='approved'
) ASC, s.id
LIMIT ?
"""
print(" ".join(str(r[0]) for r in c.execute(q, (*regions, limit))))
PY
)

echo "spots: $(echo $IDS | wc -w) ids"

total_saved=0
for sid in $IDS; do
  echo "--- spot $sid ---"
  if out=$(./venv/bin/python tools/parsers/yandex_scrape.py reviews --id "$sid" --max "$MAX" 2>&1); then
    echo "$out" | tail -4
    s=$(echo "$out" | grep 'reviews done' | sed -n 's/.*saved=\([0-9]*\).*/\1/p')
    total_saved=$((total_saved + ${s:-0}))
  else
    echo "FAIL spot $sid"
  fi
  sleep "$PAUSE"
done

echo "=== scrape saved~$total_saved $(date -Iseconds) ==="
./venv/bin/python tools/banya_review_approve_bulk.py --apply --source yandex --min-rating 3 --min-text 15 --limit 2000

./venv/bin/python - <<'PY'
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(os.getcwd()).resolve()
sys.path.insert(0, str(ROOT))
from tools.banya_regions import expand_region_tokens, GDEPAR_REVIEW_REGIONS

regions = expand_region_tokens(
    [r.strip() for r in os.environ.get("BANYA_FORCE_REGIONS", "GDEPAR").split(",") if r.strip()]
) or list(GDEPAR_REVIEW_REGIONS)
ph = ",".join("?" * len(regions))
c = sqlite3.connect("empire.db")
print("approved", c.execute("SELECT COUNT(*) FROM banya_reviews WHERE status='approved'").fetchone()[0])
print("pending", c.execute("SELECT COUNT(*) FROM banya_reviews WHERE status='pending'").fetchone()[0])
print("spots_with_approved", c.execute("SELECT COUNT(DISTINCT spot_id) FROM banya_reviews WHERE status='approved'").fetchone()[0])
q = f"""
SELECT COUNT(*) FROM banya_spots s
WHERE s.status='published' AND s.region IN ({ph})
  AND trim(coalesce(s.yandex_url,''))!=''
  AND (SELECT COUNT(*) FROM banya_reviews r WHERE r.spot_id=s.id AND r.status='approved')=0
"""
print("spots_0_approved_in_regions", c.execute(q, regions).fetchone()[0])
PY

echo "=== FORCE PIPELINE DONE $(date -Iseconds) ==="
