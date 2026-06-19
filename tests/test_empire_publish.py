import asyncio
import os
import sys

import pytest

os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")


def _fresh_main(tmp_path, monkeypatch):
    db_path = tmp_path / "empire.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    for mod in ("main", "empire_publish", "empire_flags"):
        sys.modules.pop(mod, None)
    import main

    return main


def test_publish_stub_vk_without_token(tmp_path, monkeypatch):
    main = _fresh_main(tmp_path, monkeypatch)
    import empire_publish

    async def _run():
        await main.init_db()
        async with main.async_session() as session:
            draft = main.PostDraft(
                persona_key="garden",
                text_content="test post",
                status="pending",
            )
            session.add(draft)
            await session.commit()
            await session.refresh(draft)
            return await empire_publish.publish_to_channel(
                session, content_id=draft.id, channel="vk_wall"
            )

    res = asyncio.run(_run())
    assert res.ok is False
    assert "stub" in res.detail or "VK" in res.detail


def test_publish_stop_flag(tmp_path, monkeypatch):
    main = _fresh_main(tmp_path, monkeypatch)
    import empire_flags
    import empire_publish

    flags_path = tmp_path / "flags.json"
    monkeypatch.setattr(empire_flags, "_FLAGS_PATH", flags_path)
    empire_flags.save_empire_flags({"stop_publications": True})

    async def _run():
        await main.init_db()
        async with main.async_session() as session:
            draft = main.PostDraft(persona_key="garden", text_content="x", status="pending")
            session.add(draft)
            await session.commit()
            await session.refresh(draft)
            return await empire_publish.publish_draft_multi(
                session, content_id=draft.id, channels=["tg"]
            )

    results = asyncio.run(_run())
    assert len(results) == 1
    assert results[0].ok is False
    assert results[0].detail == "stop_publications"
