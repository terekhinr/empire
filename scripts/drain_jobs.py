#!/usr/bin/env python3
"""Обработать все pending jobs и выйти."""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")


async def main():
    from main import init_db
    from empire_worker import _claim_next_job, _finish_job, _process_job

    await init_db()
    n = 0
    while True:
        job = await _claim_next_job()
        if not job:
            break
        jid = int(job.id)
        try:
            await _process_job(job)
        except Exception as exc:
            job.status = "error"
            job.error_message = str(exc)[:400]
        await _finish_job(jid, job)
        n += 1
        print(job.job_type, job.status, (job.result_json or "")[:100])
    print("drained", n)


if __name__ == "__main__":
    asyncio.run(main())
