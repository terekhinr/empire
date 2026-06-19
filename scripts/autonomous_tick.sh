#!/usr/bin/env bash
# Периодический автономный тик (cron каждые 2ч или вручную).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export EMPIRE_SKIP_EMBEDDINGS=1

./venv/bin/python scripts/run_phase1_pipeline.py
./venv/bin/python scripts/drain_jobs.py

# Черновики из spy — только вручную (дашборд). По умолчанию 0 токенов.
if [[ "${SPY_DRAFTS_PER_RUN:-0}" != "0" ]]; then
  ./venv/bin/python -c "
import asyncio, sys
sys.path.insert(0,'.')
from main import init_db, enqueue_job
async def m():
    await init_db()
    await enqueue_job('spy_to_drafts', {'limit': int('${SPY_DRAFTS_PER_RUN:-2}')})
asyncio.run(m())
"
  ./venv/bin/python scripts/drain_jobs.py
fi

echo "tick ok $(date -u +%Y-%m-%dT%H:%M:%SZ)"
