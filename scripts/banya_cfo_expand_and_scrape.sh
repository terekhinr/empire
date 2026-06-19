#!/usr/bin/env bash
# ЦФО + Питер: OSM → enrich → pubauto → форс-отзывы.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/root/.cache/ms-playwright}"
export PYTHONUNBUFFERED=1
LOG="${ROOT}/logs/banya_cfo_expand.log"
mkdir -p logs
exec >>"$LOG" 2>&1

echo "=== CFO EXPAND $(date -Iseconds) ==="

if [[ "${BANYA_CFO_SKIP_OSM:-0}" != "1" ]]; then
  echo "--- OSM import CFO (пропуск: BANYA_CFO_SKIP_OSM=1) ---"
  NEW_CFO="BEL,BRY,VLA,VOR,IVA,KLU,KOS,KUR,LIP,ORL,RYA,SMO,TAM,TVE,TUL,YAR"
  for reg in $(echo "$NEW_CFO" | tr ',' ' '); do
    ./venv/bin/python tools/parsers/osm_banyas.py --regions "$reg" || true
    sleep 12
  done
fi

ENRICH_LIMIT="${BANYA_CFO_ENRICH_LIMIT:-80}"
for reg in BEL BRY VLA VOR IVA KLU KOS KUR LIP ORL RYA SMO TAM TVE TUL YAR; do
  echo "--- enrich $reg limit=$ENRICH_LIMIT ---"
  ./venv/bin/python tools/parsers/yandex_scrape.py enrich --region "$reg" --limit "$ENRICH_LIMIT" || true
  sleep 5
done

echo "--- pubauto CFO regions ---"
for reg in BEL BRY VLA VOR IVA KLU KOS KUR LIP ORL RYA SMO TAM TVE TUL YAR; do
  ./venv/bin/python tools/banya_pubauto.py --region "$reg" --min-rating 4.0 --apply --limit 40 || true
done

echo "--- force reviews GDEPAR ---"
export BANYA_FORCE_REGIONS=GDEPAR
export BANYA_FORCE_SPOT_LIMIT="${BANYA_FORCE_SPOT_LIMIT:-80}"
bash scripts/banya_force_reviews_pipeline.sh "${1:-12}" "${2:-10}"

echo "=== CFO EXPAND DONE $(date -Iseconds) ==="
