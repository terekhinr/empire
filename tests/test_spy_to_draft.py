import asyncio
import os
import sys

os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")


def test_create_draft_from_spy_mocked(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'e.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    for m in list(sys.modules):
        if m in ("main", "spy_to_draft"):
            sys.modules.pop(m, None)
    import main

    async def fake_gen(pk, topic):
        return f"post about {topic[:30]}", "image prompt"

    async def fake_img(prompt, d_id, pk, topic_hint=None):
        return None

    monkeypatch.setattr(main, "generate_draft_content", fake_gen)
    monkeypatch.setattr(main, "generate_image", fake_img)
    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(main, "_record_topic_history", _noop)

    async def _run():
        await main.init_db()
        async with main.async_session() as session:
            sig = main.SpySignal(
                persona_key="gdepar",
                competitor="@test",
                post_text="Баня в Подмосковье",
                post_ref="http://example.com/1",
                er_proxy="0.15",
                anomaly_score="1.8",
                status="new",
            )
            session.add(sig)
            await session.commit()
            await session.refresh(sig)
            import spy_config

            monkeypatch.setattr(spy_config, "spy_live_enabled", lambda: True)
            from spy_to_draft import create_draft_from_spy

            res = await create_draft_from_spy(session, int(sig.id), skip_image=True)
            return res

    res = asyncio.run(_run())
    assert res["ok"] is True
    assert res["draft_id"] > 0


def test_pii_strip():
    from pii_validator import strip_pii

    t = strip_pii("Пишите terekhin.r@gmail.com или +7 999 123-45-67 @user")
    assert "[email]" in t
    assert "[phone]" in t
    assert "[user]" in t
