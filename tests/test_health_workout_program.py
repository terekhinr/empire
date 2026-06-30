"""Tests for workout program parser."""

from __future__ import annotations

from datetime import date

from health_workout_program import (
    get_session_for_date,
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


def test_get_session_for_date():
    session = get_session_for_date("2026-06-24")
    assert session is not None
    assert session.label.startswith("Фаза 1")
    assert session.template is not None
    assert session.template.exercises[0].exercise_label == "Жим штанги лёжа"


def test_load_real_program():
    summary = program_summary()
    assert summary["calendar_days"] == 30
    assert summary["templates"] >= 9
    templates, _ = load_program()
    assert (2, "B") in templates
    assert any(ex.is_max for ex in templates[(2, "B")].exercises)
