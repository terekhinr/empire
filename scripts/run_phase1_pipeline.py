#!/usr/bin/env python3
"""Однократный прогон phase-1 pipeline (news → spy → neuro → shorts)."""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")


async def main():
    from analytics_db import init_analytics_db
    from main import async_session, enqueue_job, init_db
    from sales_db import init_sales_db

    await init_db()
    init_analytics_db()
    init_sales_db()
    for jt, payload in (
        ("news_ingest", {}),
        ("spy_dry_run", {}),
        ("neurocomment_dry_run", {}),
        ("shorts_scripts", {"per_persona": 1}),
        ("metrics_snapshot", {}),
        ("init_sales_db", {}),
        ("yt_trends", {"persona": "stern"}),
        ("weekly_insights", {}),
    ):
        jid = await enqueue_job(jt, payload or None)
        print(f"enqueued {jt} #{jid}")
    print("Запустите empire_worker или дождитесь обработки очереди.")


if __name__ == "__main__":
    asyncio.run(main())
