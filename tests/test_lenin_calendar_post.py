"""Революционный календарь Ленина — seed для развёрнутого LLM-поста."""

from datetime import datetime
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
