import asyncio
import os
import sys

os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")


def _fresh_main(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'empire.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    for mod in list(sys.modules):
        if mod.startswith(("main", "news_rss", "telethon_spy", "neurocomment", "script_factory")):
            sys.modules.pop(mod, None)
    import main

    return main


def test_news_ingest(tmp_path, monkeypatch):
    main = _fresh_main(tmp_path, monkeypatch)

    async def _run():
        await main.init_db()
        from news_rss import ingest_rss_feeds

        async with main.async_session() as session:
            stats = await ingest_rss_feeds(session, limit_per_feed=2)
        return stats

    stats = asyncio.run(_run())
    assert stats["feeds"] >= 1


def test_spy_and_neurocomment(tmp_path, monkeypatch):
    monkeypatch.setenv("SPY_ALLOW_DRY_RUN", "1")
    main = _fresh_main(tmp_path, monkeypatch)

    async def _run():
        await main.init_db()
        from news_rss import ingest_rss_feeds
        from telethon_spy import run_spy_dry_run
        from neurocomment import run_neurocomment_dry_run

        async with main.async_session() as session:
            await ingest_rss_feeds(session, limit_per_feed=3)
            spy = await run_spy_dry_run(session, max_per_persona=2)
            nc = await run_neurocomment_dry_run(session)
        return spy, nc

    spy, nc = asyncio.run(_run())
    assert spy["inserted"] >= 0
    assert nc["inserted"] >= 0


def test_shorts_scripts(tmp_path, monkeypatch):
    main = _fresh_main(tmp_path, monkeypatch)

    async def _run():
        await main.init_db()
        from script_factory import generate_shorts_scripts

        async with main.async_session() as session:
            stats = await generate_shorts_scripts(session, personas=["garden"], per_persona=1)
        return stats

    stats = asyncio.run(_run())
    assert stats["inserted"] == 1


def test_sales_and_metrics(tmp_path, monkeypatch):
    from sales_db import init_sales_db, npd_limit_alert
    from metrics import build_ai_insights_stub

    db = tmp_path / "sales.db"
    monkeypatch.setenv("EMPIRE_SALES_DB", str(db))
    init_sales_db(db)
    alert = npd_limit_alert(db)
    assert "pct" in alert
    insights = build_ai_insights_stub()
    assert len(insights["hypotheses"]) >= 3
