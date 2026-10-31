"""Лунный посевной календарь: OCR, отбор одного фрагмента, без теории-простыни."""

from datetime import datetime
from zoneinfo import ZoneInfo

import garden_content as gc


def test_repair_ocr_spaces():
    assert gc._repair_ocr_spaces("корнепло ды") == "корнеплоды"
    assert gc._repair_ocr_spaces("Северо-За паде") == "Северо-Западе"
    assert gc._repair_ocr_spaces("тюль- панов") == "тюльпанов"


def test_rejects_theory_chunk():
    theory = (
        "Уверяю, что корнеплоды лучше сажать в период убывающей Луны. "
        "Объясняю это фотосинтезом и гравитационным притяжением."
    )
    assert not gc._chunk_is_actionable(theory)


def test_build_lunar_may27_no_triple_blockquote():
    when = datetime(2026, 5, 27, 20, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    topic, body = gc.build_lunar_calendar_post(when)
    assert body.count("<blockquote>") == 0
    assert "Кизима" not in body
    assert "Кизима" not in topic
    assert "#кизима" not in body.lower()
    assert "27 мая" in body
    assert "Фаза I" in body
    assert "началонового" not in body.lower()


def test_explicit_entry_repaired():
    when = datetime(2026, 5, 10, 20, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    _topic, body = gc.build_lunar_calendar_post(when)
    assert "огурц" in body.lower()
    assert "корнеплод" in body.lower() or "корнепло" not in body


def test_june1_uses_calendar_not_squashed_rag():
    when = datetime(2026, 6, 1, 20, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    _topic, body = gc.build_lunar_calendar_post(when)
    assert "Фаза I" in body
    assert "1 июня" in body
    assert "началонового" not in body.lower()
    assert "Длякаждого" not in body


def test_october30_is_winter_work_not_a_ban():
    when = datetime(2026, 10, 30, 20, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    _topic, body = gc.build_lunar_calendar_post(when)
    assert "30 октября" in body
    assert "Фаза I" not in body
    assert "пропол" not in body.lower()
    assert "не делают" not in body.lower()
    assert "не се" not in body.lower()
    assert len(body) >= 180


def test_rejects_squashed_ocr():
    squashed = (
        "изньсвоимрастениям, а несчитаетеэтуработу Длякаждогомесяцавкалендаредается"
        "точноевремянаступления Новолуния"
    )
    assert gc._text_looks_squashed(squashed)
    assert gc._clean_rag_excerpt(squashed) == ""
