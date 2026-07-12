"""Расписание Empire — только Europe/Moscow для weekday и слотов."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytz

import main as m

_MSK = ZoneInfo("Europe/Moscow")


def test_msk_weekday_at_utc_midnight_boundary():
    """Воскресенье 23:30 UTC = понедельник 02:30 MSK — разные weekday."""
    utc = datetime(2026, 7, 12, 23, 30, tzinfo=ZoneInfo("UTC"))
    msk = utc.astimezone(_MSK)
    assert utc.weekday() == 6  # вс UTC
    assert msk.weekday() == 0  # пн MSK


def test_resolve_scheduled_slot_uses_when_not_utc(monkeypatch):
    """_resolve_scheduled_slot берёт weekday из when=MSK, не из системного UTC."""
    import stern_content

    captured: list[int] = []

    async def fake_resolve(slot_value, *, weekday, resolve_topic_fn):
        captured.append(weekday)
        return "[stub]", "text", None, None

    monkeypatch.setattr(stern_content, "resolve_stern_slot", fake_resolve)

    when = datetime(2026, 7, 13, 9, 30, tzinfo=pytz.timezone("Europe/Moscow"))
    import asyncio

    asyncio.run(
        m._resolve_scheduled_slot(
            "stern",
            {"type": "stern_curated", "slot": "0930"},
            when=when,
        )
    )
    assert captured == [0]  # понедельник по Москве
