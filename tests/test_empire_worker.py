import asyncio
import os
import sys

os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")


def _fresh_main(tmp_path, monkeypatch):
    db_path = tmp_path / "empire.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    for mod in ("main", "empire_worker", "empire_publish"):
        sys.modules.pop(mod, None)
    import main

    return main


def test_enqueue_and_process_noop(tmp_path, monkeypatch):
    main = _fresh_main(tmp_path, monkeypatch)
    from empire_worker import _claim_next_job, _finish_job, _process_job

    async def _run():
        await main.init_db()
        jid = await main.enqueue_job("noop", {"x": 1})
        job = await _claim_next_job()
        assert job is not None
        assert int(job.id) == jid
        await _process_job(job)
        await _finish_job(jid, job)
        async with main.async_session() as session:
            row = await session.get(main.Job, jid)
            assert row.status == "done"

    asyncio.run(_run())
