"""Тесты pension raw_news."""

import asyncio

import pytest

import pension_content


def test_is_raw_news_slot_dict():
    assert pension_content.is_raw_news_slot({"type": "raw_news", "feed": "finance"}) == "finance"


def test_is_raw_news_slot_legacy_string():
    assert pension_content.is_raw_news_slot("Сводка финансовых новостей") == "finance"


def test_format_digest_empty():
    body = pension_content._format_digest("finance", [])
    assert "RSS" in body or "пусто" in body.lower()


def test_build_raw_news_prebuilt(tmp_path, monkeypatch):
    import sys

    db_path = tmp_path / "empire.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    for mod in ("main",):
        sys.modules.pop(mod, None)
    import main

    async def _run():
        await main.init_db()
        async with main.async_session() as session:
            session.add(
                main.NewsItem(
                    url_hash="abc123",
                    url="https://example.com/1",
                    title="ЦБ поднял ставку",
                    source_feed="test",
                    category="finance",
                )
            )
            await session.commit()
            return await pension_content.build_raw_news_prebuilt(session, "finance")

    topic, body = asyncio.run(_run())
    assert "[RAW:finance]" in topic
    assert "ЦБ" in body
