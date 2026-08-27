"""Tests for workout program parser."""

from __future__ import annotations

from datetime import date

from health_workout_program import (
    build_rolling_calendar,
    default_anchor,
    get_session_for_date,
    list_programs,
    load_program,
    parse_program,
    program_summary,
)


SAMPLE = """\
# Программа: Фаза 1 — Сушка

meta:
  калории: 2200 ккал

## День A — Сила

- жим_штанги_лежа | 4×4–6 | вес 105–110 кг | отдых 3 мин
- отдых | 0×0 | прогулка

# Мастер-календарь
- [ ] [[2026-06-24]] (Ср) — Фаза 1 / День A
"""


def test_parse_exercise_and_calendar():
    templates, calendar = parse_program(SAMPLE)
    assert len(calendar) == 1
    assert calendar[0].on == date(2026, 6, 24)
    tpl = templates[(1, "A")]
    assert tpl.title == "Сила"
    assert tpl.exercises[0].exercise_key == "жим_штанги_лежа"
    assert tpl.exercises[0].sets == 4
    assert tpl.exercises[0].reps_min == 4
    assert tpl.exercises[0].reps_max == 6
    assert tpl.exercises[0].suggested_weight_kg == 107.5
    assert tpl.exercises[1].is_rest


def test_get_session_for_date_with_anchor():
    session = get_session_for_date("2026-06-24", anchor="2026-06-24", start_day="A")
    assert session is not None
    assert session.label.startswith("Фаза 1")
    assert session.template is not None
    assert session.template.exercises[0].exercise_label == "Жим штанги лёжа"


def test_load_real_program():
    summary = program_summary(anchor="2026-06-24", start_day="A")
    assert summary["calendar_days"] == 30
    assert summary["templates"] >= 9
    templates, _ = load_program()
    assert (2, "B") in templates
    assert any(ex.is_max for ex in templates[(2, "B")].exercises)


def test_rolling_outside_hall_starts_on_anchor():
    anchor = "2026-07-20"  # Monday
    cal = build_rolling_calendar("outside_hall", anchor=anchor, start_day="A")
    assert len(cal) == 9
    assert cal[0].on == date(2026, 7, 20)
    assert cal[0].day == "A"
    assert cal[1].on == date(2026, 7, 22)  # Wed
    assert cal[1].day == "B"
    assert cal[2].on == date(2026, 7, 24)  # Fri
    assert cal[2].day == "C"


def test_outside_hall_start_day_rotation():
    anchor = "2026-07-20"
    session = get_session_for_date("2026-07-20", "outside_hall", anchor=anchor, start_day="B")
    assert session is not None
    assert session.day == "B"
    session_c = get_session_for_date("2026-07-24", "outside_hall", anchor=anchor, start_day="B")
    assert session_c is not None
    assert session_c.day == "A"


def test_outside_hall_program():
    anchor = default_anchor(date(2026, 7, 17))
    summary = program_summary("outside_hall", anchor=anchor.isoformat(), start_day="A")
    assert summary["title"] == "Работа вне зала"
    assert summary["calendar_days"] == 9
    assert summary["note_prefix"] == "внезала подход"
    assert summary["start"] == anchor.isoformat()
    templates, calendar = load_program("outside_hall")
    assert (1, "A") in templates
    assert (1, "B") in templates
    assert (1, "C") in templates
    keys = {ex.exercise_key for ex in templates[(1, "A")].exercises}
    assert "модифицированное_скручивание_макгилла" in keys
    assert "боковая_планка_макгилла" in keys
    assert "упражнение_собака_птица" in keys
    assert "отжимания_от_пола_с_резиновой_петлей_на_спине" in keys
    assert "челночный_бег_отработка_техники" in keys
    assert "тяга_резиновой_петли_к_поясу_стоя" in keys
    assert "тяга_в_петлях_trx_к_поясу" in keys
    day_b = {ex.exercise_key for ex in templates[(1, "B")].exercises}
    assert "ягодичный_мостик_с_резиновой_петлей_на_бедрах" in day_b
    assert "тяга_резиновой_петли_к_поясу_стоя" in day_b
    assert "т_разведения_рук_в_петлях_trx" in day_b
    assert "наклоны_гудморнинг_с_резиной" not in day_b
    day_c = {ex.exercise_key for ex in templates[(1, "C")].exercises}
    assert "тяга_резиновой_петли_к_поясу_стоя" in day_c
    assert "тяга_в_петлях_trx_к_поясу" in day_c
    session = get_session_for_date(anchor.isoformat(), "outside_hall", anchor=anchor, start_day="A")
    assert session is not None
    assert session.program_id == "outside_hall"
    assert session.day == "A"
    assert any(ex.is_max for ex in session.template.exercises)


def test_time_hold_detection():
    templates, _ = load_program("outside_hall")
    by_key = {ex.exercise_key: ex for ex in templates[(1, "A")].exercises}
    assert by_key["классическая_планка_на_предплечьях"].is_time_hold
    assert by_key["классическая_планка_на_предплечьях"].hold_seconds == 60
    assert by_key["боковая_планка_макгилла"].is_time_hold
    assert by_key["модифицированное_скручивание_макгилла"].is_time_hold is False
    assert by_key["модифицированное_скручивание_макгилла"].hold_seconds == 10
    assert by_key["упражнение_собака_птица"].is_time_hold is False
    assert by_key["упражнение_собака_птица"].hold_seconds == 10


def test_list_programs_includes_both():
    programs = list_programs()
    ids = {p["id"] for p in programs}
    assert "gym_2026" in ids
    assert "outside_hall" in ids
