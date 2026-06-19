from datetime import datetime
from zoneinfo import ZoneInfo

import scheduler_slots as ss


def test_slot_dedup(tmp_path, monkeypatch):
    state = tmp_path / "scheduler_slots_fired.json"
    monkeypatch.setattr(ss, "_STATE_PATH", state)
    when = datetime(2026, 6, 9, 9, 30, tzinfo=ZoneInfo("Europe/Moscow"))
    assert not ss.already_fired("stern", when, "09:30")
    ss.mark_fired("stern", when, "09:30", draft_id=1, topic="[План на неделю]")
    assert ss.already_fired("stern", when, "09:30")
    assert not ss.already_fired("stern", when, "10:00")


def test_valid_post_text():
    import stern_week_arc as swa

    assert not swa.is_valid_scheduled_post_text("🛑 Ошибка API")
    assert swa.is_valid_scheduled_post_text("🔥 " + "а" * 250)
