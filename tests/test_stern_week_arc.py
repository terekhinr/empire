import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import stern_week_arc as swa


def test_weekly_recap_without_plan(tmp_path, monkeypatch):
    state_file = tmp_path / "stern_week_state.json"
    monkeypatch.setattr(swa, "_STATE_PATH", state_file)
    topic, body = swa.build_weekly_recap_post(
        when=datetime(2026, 6, 7, 19, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    )
    assert "Итоги недели" in topic
    assert "план на понедельник не выходил" in body.lower()
    assert "пн 09:30" in body
    assert "ср 15:00" in body


def test_save_plan_and_recap(tmp_path, monkeypatch):
    state_file = tmp_path / "stern_week_state.json"
    monkeypatch.setattr(swa, "_STATE_PATH", state_file)
    when = datetime(2026, 6, 2, 9, 30, tzinfo=ZoneInfo("Europe/Moscow"))
    plan_text = (
        "🔥 План недели\n\n"
        "Пн: гиря 16 кг, 5×5 рывок\n"
        "Вт: отдых активный\n"
        "Тест недели: 5 минут burpee — считать повторы в субботу"
    )
    swa.save_weekly_plan(topic="[План на неделю]", text=plan_text, when=when, draft_id=101)
    topic, body = swa.build_weekly_recap_post(
        when=datetime(2026, 6, 7, 19, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    )
    assert "План недели" in body
    assert "Тест недели" in body
    assert "план на понедельник не выходил" not in body.lower()


def test_extract_test_name_from_html():
    text = (
        "<b>📏 Тест недели: Проверка стабильности корпуса</b> \n\n"
        "Крепкий корпус — основа для работы с гирями."
    )
    assert swa._extract_test_name(text) == "Проверка стабильности корпуса"


def test_topic_display_label_spy_and_rubric():
    spy = swa._topic_display_label(
        "[spy_inspired] Telethon не подключён — свободная тема",
        "🔥 Почему твой кор не держит спину (и как это исправить) Кор — это не просто",
    )
    assert "Telethon" not in spy
    assert "кор" in spy.lower()
    assert "кубики" not in spy.lower()

    rubric = swa._topic_display_label(
        "[Историческое наследие] Герман Муратов: Отец силового жонглирования "
        "(id=legacy_062_muratov)",
        "",
    )
    assert rubric.startswith("Герман Муратов")
    assert "(id=" not in rubric


def test_mark_post_published_adds_links(tmp_path, monkeypatch):
    state_file = tmp_path / "stern_week_state.json"
    monkeypatch.setattr(swa, "_STATE_PATH", state_file)
    when = datetime(2026, 6, 10, 15, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    test_text = "<b>📏 Тест недели: Планка 60 сек</b>"
    swa.save_weekly_test(
        topic="[Тест недели]", text=test_text, when=when, draft_id=55
    )
    swa.mark_post_published(55, 12345, when=when)
    topic, body = swa.build_weekly_recap_post(
        when=datetime(2026, 6, 14, 19, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    )
    assert 'href="https://t.me/c/2024827297/12345"' in body
    assert "Планка 60 сек" in body


def test_stern_weekly_recap_slot():
    import stern_content

    async def _topic(*_a, **_k):
        return "unused"

    topic, prebuilt, img, seed = asyncio.run(
        stern_content.resolve_stern_slot(
            {"type": "weekly_recap"}, weekday=6, resolve_topic_fn=_topic
        )
    )
    assert prebuilt
    assert seed is None
    assert "Итоги недели" in prebuilt
    assert "<b>" in prebuilt
