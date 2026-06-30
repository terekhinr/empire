"""Parse workout program markdown and resolve sessions by date."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from health_db import STRENGTH_EXERCISES

BASE_DIR = Path(__file__).resolve().parent
PROGRAM_PATH = BASE_DIR / "docs" / "health" / "workout_program_2026.md"

CALENDAR_LINE_RE = re.compile(
    r"^- \[[ xX]\] \[\[(\d{4}-\d{2}-\d{2})\]\].*?—\s*(.+?)\s*$"
)
SESSION_LABEL_RE = re.compile(r"Фаза\s*(\d+)\s*/\s*День\s*([ABCАВС])", re.I)
DAY_HEADER_RE = re.compile(r"^##\s+День\s+([ABCАВС])\s+—\s+(.+)$", re.I)
PHASE_HEADER_RE = re.compile(r"^#\s+Программа:\s+Фаза\s+(\d+)\s+—\s+(.+)$", re.I)
EXERCISE_LINE_RE = re.compile(r"^-\s+(\S+)\s*\|\s*(.+)$")
SETS_REPS_RE = re.compile(r"^(\d+)\s*[×xX]\s*(.+)$")
WEIGHT_RANGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*[–—-]\s*(\d+(?:[.,]\d+)?)\s*кг")
WEIGHT_SINGLE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*кг", re.I)

_CYR_TO_LAT = {"А": "A", "В": "B", "С": "C", "а": "A", "в": "B", "с": "C"}


def _norm_day(letter: str) -> str:
    return _CYR_TO_LAT.get(letter, letter.upper())


@dataclass
class WorkoutExercise:
    exercise_key: str
    prescription: str
    detail: str
    sets: int = 0
    reps: int | None = None
    reps_min: int | None = None
    reps_max: int | None = None
    is_max: bool = False
    suggested_weight_kg: float | None = None

    @property
    def exercise_label(self) -> str:
        return STRENGTH_EXERCISES.get(self.exercise_key, self.exercise_key)

    @property
    def is_rest(self) -> bool:
        return self.exercise_key == "отдых"


@dataclass
class WorkoutDayTemplate:
    phase: int
    phase_title: str
    day: str
    title: str
    meta: dict[str, str] = field(default_factory=dict)
    exercises: list[WorkoutExercise] = field(default_factory=list)


@dataclass
class CalendarEntry:
    on: date
    label: str
    phase: int
    day: str
    note: str = ""


@dataclass
class WorkoutSession:
    on: date
    label: str
    phase: int
    day: str
    template: WorkoutDayTemplate | None
    note: str = ""


def _parse_sets_reps(prescription: str) -> tuple[int, int | None, int | None, int | None, bool]:
    m = SETS_REPS_RE.match(prescription.strip())
    if not m:
        return 0, None, None, None, False
    sets = int(m.group(1))
    reps_part = m.group(2).strip().upper()
    if reps_part in ("МАКС", "MAX"):
        return sets, None, None, None, True
    if "–" in reps_part or "-" in reps_part:
        parts = re.split(r"[–-]", reps_part)
        if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
            lo, hi = int(parts[0]), int(parts[1])
            return sets, (lo + hi) // 2, lo, hi, False
    digits = re.findall(r"\d+", reps_part)
    if digits:
        val = int(digits[0])
        return sets, val, val, val, False
    return sets, None, None, None, False


def _parse_weight(detail: str) -> float | None:
    rm = WEIGHT_RANGE_RE.search(detail)
    if rm:
        lo = float(rm.group(1).replace(",", "."))
        hi = float(rm.group(2).replace(",", "."))
        return round((lo + hi) / 2, 1)
    for m in WEIGHT_SINGLE_RE.finditer(detail):
        return float(m.group(1).replace(",", "."))
    return None


def _parse_exercise_line(line: str) -> WorkoutExercise | None:
    m = EXERCISE_LINE_RE.match(line.strip())
    if not m:
        return None
    key = m.group(1).strip()
    rest = m.group(2).strip()
    parts = [p.strip() for p in rest.split("|")]
    prescription = parts[0] if parts else ""
    detail = " | ".join(parts[1:]) if len(parts) > 1 else ""
    sets, reps, rmin, rmax, is_max = _parse_sets_reps(prescription)
    return WorkoutExercise(
        exercise_key=key,
        prescription=prescription,
        detail=detail,
        sets=sets,
        reps=reps,
        reps_min=rmin,
        reps_max=rmax,
        is_max=is_max,
        suggested_weight_kg=_parse_weight(detail),
    )


def _parse_meta_block(lines: list[str]) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in lines:
        if not line.strip() or line.strip() == "meta:":
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta


def parse_program(text: str) -> tuple[dict[tuple[int, str], WorkoutDayTemplate], list[CalendarEntry]]:
    templates: dict[tuple[int, str], WorkoutDayTemplate] = {}
    calendar: list[CalendarEntry] = []

    phase_num = 0
    phase_title = ""
    phase_meta: dict[str, str] = {}
    in_meta = False
    meta_lines: list[str] = []
    current_day: WorkoutDayTemplate | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("# Мастер-календарь"):
            in_meta = False
            current_day = None
            continue

        cal = CALENDAR_LINE_RE.match(line)
        if cal:
            d = date.fromisoformat(cal.group(1))
            label = cal.group(2).strip()
            sm = SESSION_LABEL_RE.search(label)
            note = ""
            if "(" in label:
                note = label[label.find("(") :].strip("() ")
                label = label[: label.find("(")].strip()
            if sm:
                calendar.append(
                    CalendarEntry(
                        on=d,
                        label=label,
                        phase=int(sm.group(1)),
                        day=_norm_day(sm.group(2)),
                        note=note,
                    )
                )
            continue

        pm = PHASE_HEADER_RE.match(line)
        if pm:
            in_meta = False
            current_day = None
            phase_num = int(pm.group(1))
            phase_title = pm.group(2).strip()
            phase_meta = {}
            continue

        if line.strip() == "meta:":
            in_meta = True
            meta_lines = []
            continue

        if in_meta:
            if line.startswith("## ") or line.startswith("# ") or line.startswith("---"):
                phase_meta = _parse_meta_block(meta_lines)
                in_meta = False
            else:
                meta_lines.append(line)
                continue

        dm = DAY_HEADER_RE.match(line)
        if dm and phase_num:
            day = _norm_day(dm.group(1))
            current_day = WorkoutDayTemplate(
                phase=phase_num,
                phase_title=phase_title,
                day=day,
                title=dm.group(2).strip(),
                meta=dict(phase_meta),
            )
            templates[(phase_num, day)] = current_day
            continue

        if current_day and line.startswith("- "):
            ex = _parse_exercise_line(line)
            if ex:
                current_day.exercises.append(ex)

    return templates, calendar


@lru_cache(maxsize=1)
def load_program() -> tuple[dict[tuple[int, str], WorkoutDayTemplate], list[CalendarEntry]]:
    path = PROGRAM_PATH
    if not path.is_file():
        return {}, []
    return parse_program(path.read_text(encoding="utf-8"))


def get_calendar() -> list[CalendarEntry]:
    return load_program()[1]


def get_session_for_date(on: date | str) -> WorkoutSession | None:
    if isinstance(on, str):
        on = date.fromisoformat(on)
    templates, calendar = load_program()
    for entry in calendar:
        if entry.on == on:
            template = templates.get((entry.phase, entry.day))
            return WorkoutSession(
                on=on,
                label=entry.label,
                phase=entry.phase,
                day=entry.day,
                template=template,
                note=entry.note,
            )
    return None


def next_scheduled_session(after: date | None = None) -> WorkoutSession | None:
    after = after or date.today()
    for entry in get_calendar():
        if entry.on >= after:
            templates = load_program()[0]
            return WorkoutSession(
                on=entry.on,
                label=entry.label,
                phase=entry.phase,
                day=entry.day,
                template=templates.get((entry.phase, entry.day)),
                note=entry.note,
            )
    return None


def program_summary() -> dict[str, Any]:
    templates, calendar = load_program()
    return {
        "path": str(PROGRAM_PATH),
        "phases": len({t.phase for t in templates.values()}),
        "templates": len(templates),
        "calendar_days": len(calendar),
        "start": calendar[0].on.isoformat() if calendar else None,
        "end": calendar[-1].on.isoformat() if calendar else None,
    }


def _exercise_to_dict(ex: WorkoutExercise) -> dict[str, Any]:
    return {
        "exercise_key": ex.exercise_key,
        "exercise_label": ex.exercise_label,
        "prescription": ex.prescription,
        "detail": ex.detail,
        "sets": ex.sets,
        "reps": ex.reps,
        "reps_min": ex.reps_min,
        "reps_max": ex.reps_max,
        "is_max": ex.is_max,
        "is_rest": ex.is_rest,
        "suggested_weight_kg": ex.suggested_weight_kg,
    }


def session_to_dict(session: WorkoutSession | None) -> dict[str, Any] | None:
    if not session:
        return None
    tpl = session.template
    return {
        "on": session.on.isoformat(),
        "label": session.label,
        "phase": session.phase,
        "day": session.day,
        "note": session.note,
        "title": tpl.title if tpl else None,
        "meta": tpl.meta if tpl else {},
        "exercises": [_exercise_to_dict(ex) for ex in (tpl.exercises if tpl else [])],
    }


def calendar_to_dict() -> list[dict[str, Any]]:
    return [
        {
            "on": e.on.isoformat(),
            "label": e.label,
            "phase": e.phase,
            "day": e.day,
            "note": e.note,
        }
        for e in get_calendar()
    ]
