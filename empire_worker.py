"""Фоновый worker: очередь jobs в empire.db (ТЗ FINAL §3.2)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone

from sqlalchemy import select

from analytics_db import init_analytics_db, log_event
from empire_flags import load_empire_flags
from main import Job, async_session, init_db

logger = logging.getLogger("empire.worker")
POLL_SEC = float(os.getenv("EMPIRE_WORKER_POLL_SEC", "12"))


async def _process_job(job: Job) -> None:
    payload = {}
    if job.payload_json:
        try:
            payload = json.loads(job.payload_json)
        except json.JSONDecodeError:
            payload = {}
    jt = (job.job_type or "").strip()
    if jt == "generate_dzen_rss":
        from rss_maker import generate_all_dzen_rss

        await generate_all_dzen_rss()
        job.result_json = json.dumps({"ok": True})
    elif jt == "media_gc":
        from empire_media_gc import run_media_gc

        n = run_media_gc()
        job.result_json = json.dumps({"deleted": n})
    elif jt == "neurocomment_dry_run":
        from neurocomment import run_neurocomment_dry_run

        async with async_session() as session:
            stats = await run_neurocomment_dry_run(session)
        job.result_json = json.dumps(stats)
    elif jt == "news_ingest":
        from news_rss import ingest_rss_feeds

        async with async_session() as session:
            stats = await ingest_rss_feeds(session)
        job.result_json = json.dumps(stats)
    elif jt == "spy_dry_run":
        from telethon_spy import run_spy_collect

        async with async_session() as session:
            stats = await run_spy_collect(session)
        job.result_json = json.dumps(stats)
    elif jt == "shorts_scripts":
        from script_factory import generate_shorts_scripts

        personas = payload.get("personas")
        async with async_session() as session:
            stats = await generate_shorts_scripts(
                session, personas=personas, per_persona=int(payload.get("per_persona", 2))
            )
        job.result_json = json.dumps(stats)
    elif jt == "metrics_snapshot":
        from metrics import snapshot_daily_subs

        snapshot_daily_subs()
        job.result_json = json.dumps({"ok": True})
    elif jt == "init_sales_db":
        from sales_db import init_sales_db

        init_sales_db()
        job.result_json = json.dumps({"ok": True})
    elif jt == "spy_to_drafts":
        from spy_to_draft import batch_drafts_from_spy

        lim = int(payload.get("limit", 0)) or None
        skip_img = bool(payload.get("skip_image"))
        async with async_session() as session:
            stats = await batch_drafts_from_spy(session, limit=lim, skip_image=skip_img)
        job.result_json = json.dumps(stats)
    elif jt == "yt_trends":
        from scout_yt import fetch_yt_trends_stub

        persona = payload.get("persona", "stern")
        stats = fetch_yt_trends_stub(persona=persona)
        job.result_json = json.dumps({"items": len(stats.get("items", []))})
    elif jt == "weekly_insights":
        from metrics import save_weekly_insights_file

        path = save_weekly_insights_file()
        job.result_json = json.dumps({"path": path})
    elif jt == "noop":
        job.result_json = json.dumps({"ok": True})
    else:
        job.status = "error"
        job.error_message = f"unknown_job_type:{jt}"
        return
    job.status = "done"
    job.error_message = None


async def _claim_next_job() -> Job | None:
    async with async_session() as session:
        stmt = (
            select(Job)
            .where(Job.status == "pending")
            .order_by(Job.id.asc())
            .limit(1)
        )
        job = (await session.execute(stmt)).scalar_one_or_none()
        if not job:
            return None
        job.status = "running"
        job.attempts = int(job.attempts or 0) + 1
        job.started_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(job)
        return job


async def _finish_job(job_id: int, job: Job) -> None:
    async with async_session() as session:
        row = await session.get(Job, job_id)
        if not row:
            return
        row.status = job.status
        row.error_message = job.error_message
        row.result_json = job.result_json
        row.finished_at = datetime.now(timezone.utc)
        await session.commit()


async def worker_loop() -> None:
    await init_db()
    init_analytics_db()
    logger.info("empire_worker started poll=%.0fs", POLL_SEC)
    while True:
        flags = load_empire_flags()
        if flags.get("stop_worker"):
            await asyncio.sleep(POLL_SEC)
            continue
        job = await _claim_next_job()
        if not job:
            await asyncio.sleep(POLL_SEC)
            continue
        jid = int(job.id)
        try:
            if job.job_type == "neurocomment_dry_run" and flags.get("stop_neurocomment"):
                job.status = "cancelled"
                job.error_message = "stop_neurocomment"
            else:
                await _process_job(job)
        except Exception as exc:
            logger.exception("job %s failed", jid)
            job.status = "error"
            job.error_message = str(exc)[:500]
        await _finish_job(jid, job)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
