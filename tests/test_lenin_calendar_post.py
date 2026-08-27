"""Революционный календарь Ленина — seed для развёрнутого LLM-поста."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import lenin_content as lc

_MSK = ZoneInfo("Europe/Moscow")


def test_make_calendar_seed_may12():
    when = datetime(2026, 5, 12, 8, 30, tzinfo=_MSK)
    seed = lc.make_calendar_seed(when)
    assert seed is not None
    assert seed["_kind"] == "lenin_calendar"
    assert "#Вэтотдень" in seed["topic"]
    assert "12 мая 1923 года" in seed["headline"]
    assert "по старому календарю 29 апреля" in seed["opening"]
    assert "Горки" in seed["event_desc"]


def test_calendar_prompt_block_structure():
    when = datetime(2026, 5, 12, 8, 30, tzinfo=_MSK)
    seed = lc.make_calendar_seed(when)
    block = lc.calendar_prompt_block(seed)
    assert "Исторический контекст:" in block
    assert "Вывод:" in block
    assert "blockquote" in block
    assert "#Вэтотдень" in block


def test_calculate_old_style_may12_1923():
    assert lc.calculate_old_style(12, 5, 1923) == "29 апреля"


def test_resolve_lenin_calendar_prebuilt_not_llm():
    import asyncio

    topic, text, img, seed = asyncio.run(
        lc.resolve_lenin_slot({"type": "lenin_calendar"}, weekday=0)
    )
    assert seed is None
    assert text
    assert "[#Вэтотдень]" in topic
    assert "календарь" in text.lower()
    assert lc.is_calendar_topic("[#Вэтотдень] Революционный календарь: 12 мая 1923 года")
    assert lc.is_calendar_topic("[В этот день] Революционный календарь.")
    assert not lc.is_calendar_topic("[Марксистский анализ] что-то")


def test_calendar_stub_passes_calendar_floor_not_quote_floor():
    import main as empire_main
    from rubric_posts import MIN_CALENDAR_BODY_CHARS, MIN_CURATED_BODY_CHARS

    when = datetime(2026, 8, 27, 8, 30, tzinfo=ZoneInfo("Europe/Moscow"))
    topic, body = lc.build_revolutionary_calendar_post(when)
    assert MIN_CALENDAR_BODY_CHARS < MIN_CURATED_BODY_CHARS
    assert not empire_main._curated_body_too_short(body, topic_raw=topic)
    assert empire_main._curated_body_too_short(body, topic_raw="[Ленин в кино] test")


def test_lenin_pool_falls_back_to_default(tmp_path, monkeypatch):
    import shutil

    import main as empire_main

    pool = tmp_path / "pool"
    pool.mkdir()
    default = tmp_path / "default.jpg"
    src = Path("media/lenin/rubrics/_default_lenin.jpg")
    shutil.copy(src, default)
    monkeypatch.setattr(empire_main, "LENIN_POOL_DIR", str(pool))
    monkeypatch.setattr(empire_main, "LENIN_DEFAULT_IMAGE", str(default))
    monkeypatch.chdir(tmp_path)
    got = empire_main._pick_random_lenin_from_pool(999001)
    assert got
    assert Path(tmp_path / got).is_file()
    assert Path(tmp_path / got).stat().st_size > 50_000


def test_calendar_autopublish_not_blocked_with_photo(tmp_path):
    from types import SimpleNamespace

    import main as empire_main

    cfg = empire_main._load_auto_publish_config()
    assert cfg["rubrics"]["lenin_calendar"]["enabled"] is True
    when = datetime(2026, 8, 27, 8, 30, tzinfo=_MSK)
    topic, body = lc.build_revolutionary_calendar_post(when)
    img = tmp_path / "cal.jpg"
    img.write_bytes(Path("media/lenin/rubrics/_default_lenin.jpg").read_bytes())
    draft = SimpleNamespace(regen_count=0, bad_image_count=0)
    rules, rubric = empire_main._auto_publish_rules_for(cfg, "lenin", topic)
    assert rubric.get("enabled")
    reason = empire_main._auto_publish_reason_blocked(
        cfg, "lenin", body, str(img), draft, topic_raw=topic, rules_override=rules
    )
    assert reason is None, reason
    assert (
        empire_main._auto_publish_reason_blocked(
            cfg, "lenin", body, None, draft, topic_raw=topic, rules_override=rules
        )
        == "no_image"
    )
