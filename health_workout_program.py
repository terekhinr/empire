"""Parse workout program markdown and resolve sessions by date."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from health_db import STRENGTH_EXERCISES

BASE_DIR = Path(__file__).resolve().parent

PROGRAM_REGISTRY: dict[str, dict[str, Any]] = {
    "gym_2026": {
        "id": "gym_2026",
        "title": "Программа 2026",
        "short": "Зал",
        "path": BASE_DIR / "docs" / "health" / "workout_program_2026.md",
        "note_prefix": "подход",
    },
    "outside_hall": {
        "id": "outside_hall",
        "title": "Работа вне зала",
        "short": "Вне зала",
        "path": BASE_DIR / "docs" / "health" / "workout_program_outside_hall.md",
        "note_prefix": "внезала подход",
        "rolling_sessions": 9,
    },
}
SLOT_WEEKDAYS = (0, 2, 4)  # Mon, Wed, Fri
DAY_CYCLE = ("A", "B", "C")
HOLD_SEC_RE = re.compile(r"(\d+)\s*сек", re.I)
DEFAULT_PROGRAM_ID = "gym_2026"
# Backward-compatible alias
PROGRAM_PATH = PROGRAM_REGISTRY[DEFAULT_PROGRAM_ID]["path"]

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


def resolve_program_id(program_id: str | None = None) -> str:
    pid = (program_id or DEFAULT_PROGRAM_ID).strip() or DEFAULT_PROGRAM_ID
    if pid not in PROGRAM_REGISTRY:
        raise ValueError(f"unknown_program:{pid}")
    return pid


def get_program_meta(program_id: str | None = None) -> dict[str, Any]:
    pid = resolve_program_id(program_id)
    meta = PROGRAM_REGISTRY[pid]
    return {
        "id": meta["id"],
        "title": meta["title"],
        "short": meta["short"],
        "note_prefix": meta["note_prefix"],
        "path": str(meta["path"]),
    }


def list_programs() -> list[dict[str, Any]]:
    out = []
    for pid in PROGRAM_REGISTRY:
        meta = get_program_meta(pid)
        summary = program_summary(pid)
        out.append({**meta, **summary})
    return out


def program_note_prefix(program_id: str | None = None) -> str:
    return get_program_meta(program_id)["note_prefix"]


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
    is_time_hold: bool = False
    hold_seconds: int | None = None

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
    program_id: str = DEFAULT_PROGRAM_ID


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


def _detect_time_hold(
    exercise_key: str,
    detail: str,
    reps: int | None,
    reps_min: int | None,
    reps_max: int | None,
) -> tuple[bool, int | None]:
    """Return (is_time_based, hold_seconds).

    is_time_based — лог в секундах (планка 60 сек).
    hold_seconds — длительность таймера; у Макгилла может быть
    при логе в повторах (8–10 повт × удержание 10 сек).
    """
    detail_l = detail.lower()
    key_l = exercise_key.lower()
    hold_from_text: int | None = None
    m = HOLD_SEC_RE.search(detail_l)
    if m:
        hold_from_text = int(m.group(1))

    if "сек на каждую сторону" in detail_l:
        return True, reps_max or reps_min or reps or hold_from_text
    if "планка" in key_l and reps and reps >= 30:
        return True, hold_from_text or reps
    if hold_from_text and ("статик" in detail_l or (reps is not None and reps >= 30)):
        return True, hold_from_text
    if hold_from_text and reps is not None and reps >= 30:
        return True, hold_from_text

    # Гибрид: повторы + таймер удержания (Макгилл, собака-птица)
    if hold_from_text and (
        "удержан" in detail_l
        or "макгилл" in key_l
        or "собака_птица" in key_l
    ):
        return False, hold_from_text

    return False, hold_from_text


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
    is_time_hold, hold_seconds = _detect_time_hold(key, detail, reps, rmin, rmax)
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
        is_time_hold=is_time_hold,
        hold_seconds=hold_seconds,
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


def default_anchor(today: date | None = None) -> date:
    """Next Monday on or after today (if today is Monday — next week's Monday)."""
    today = today or date.today()
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _snap_to_slot(d: date, slot_weekdays: tuple[int, ...] = SLOT_WEEKDAYS) -> date:
    if d.weekday() in slot_weekdays:
        return d
    for _ in range(7):
        d += timedelta(days=1)
        if d.weekday() in slot_weekdays:
            return d
    return d


def _generate_slot_dates(
    anchor: date,
    count: int,
    slot_weekdays: tuple[int, ...] = SLOT_WEEKDAYS,
) -> list[date]:
    dates: list[date] = []
    d = _snap_to_slot(anchor, slot_weekdays)
    while len(dates) < count:
        if d.weekday() in slot_weekdays:
            dates.append(d)
        d += timedelta(days=1)
    return dates


def _outside_session_specs(start_day: str, count: int) -> list[tuple[int, str, str, str]]:
    day = _norm_day(start_day)
    if day not in DAY_CYCLE:
        day = "A"
    start_idx = DAY_CYCLE.index(day)
    specs: list[tuple[int, str, str, str]] = []
    for i in range(count):
        letter = DAY_CYCLE[(start_idx + i) % 3]
        specs.append((1, letter, f"Фаза 1 / День {letter}", ""))
    return specs


def _rotate_specs_to_start_day(
    specs: list[tuple[int, str, str, str]],
    start_day: str,
) -> list[tuple[int, str, str, str]]:
    day = _norm_day(start_day)
    if day not in DAY_CYCLE or not specs:
        return specs
    start_idx = next((i for i, s in enumerate(specs) if s[1] == day), 0)
    return specs[start_idx:] + specs[:start_idx]


def _static_session_specs(program_id: str) -> list[tuple[int, str, str, str]]:
    _, calendar = load_program(program_id)
    return [(e.phase, e.day, e.label, e.note) for e in calendar]


def build_rolling_calendar(
    program_id: str | None = None,
    anchor: date | str | None = None,
    start_day: str | None = None,
) -> list[CalendarEntry]:
    pid = resolve_program_id(program_id)
    meta = PROGRAM_REGISTRY[pid]
    slot = tuple(meta.get("slot_weekdays", SLOT_WEEKDAYS))
    start = _norm_day(start_day or "A")

    if pid == "outside_hall":
        count = int(meta.get("rolling_sessions", 9))
        specs = _outside_session_specs(start, count)
    else:
        specs = _rotate_specs_to_start_day(_static_session_specs(pid), start)
        count = len(specs)

    if isinstance(anchor, str):
        anchor = date.fromisoformat(anchor)
    anchor_d = _snap_to_slot(anchor or default_anchor(), slot)
    dates = _generate_slot_dates(anchor_d, count, slot)

    return [
        CalendarEntry(on=d, label=label, phase=phase, day=day, note=note)
        for d, (phase, day, label, note) in zip(dates, specs)
    ]


def resolve_schedule(
    program_id: str | None = None,
    anchor: date | str | None = None,
    start_day: str | None = None,
) -> tuple[date, str, list[CalendarEntry]]:
    pid = resolve_program_id(program_id)
    start = _norm_day(start_day or "A")
    if isinstance(anchor, str):
        anchor = date.fromisoformat(anchor)
    cal = build_rolling_calendar(pid, anchor, start)
    anchor_d = cal[0].on if cal else _snap_to_slot(anchor or default_anchor())
    return anchor_d, start, cal


@lru_cache(maxsize=8)
def load_program(
    program_id: str | None = None,
) -> tuple[dict[tuple[int, str], WorkoutDayTemplate], list[CalendarEntry]]:
    pid = resolve_program_id(program_id)
    path = PROGRAM_REGISTRY[pid]["path"]
    if not path.is_file():
        return {}, []
    return parse_program(path.read_text(encoding="utf-8"))


def get_calendar(
    program_id: str | None = None,
    anchor: date | str | None = None,
    start_day: str | None = None,
) -> list[CalendarEntry]:
    return resolve_schedule(program_id, anchor, start_day)[2]


def get_session_for_date(
    on: date | str,
    program_id: str | None = None,
    anchor: date | str | None = None,
    start_day: str | None = None,
) -> WorkoutSession | None:
    if isinstance(on, str):
        on = date.fromisoformat(on)
    pid = resolve_program_id(program_id)
    templates, _ = load_program(pid)
    _, _, calendar = resolve_schedule(pid, anchor, start_day)
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
                program_id=pid,
            )
    return None


def next_scheduled_session(
    after: date | None = None,
    program_id: str | None = None,
    anchor: date | str | None = None,
    start_day: str | None = None,
) -> WorkoutSession | None:
    after = after or date.today()
    pid = resolve_program_id(program_id)
    templates, _ = load_program(pid)
    _, _, calendar = resolve_schedule(pid, anchor, start_day)
    for entry in calendar:
        if entry.on >= after:
            return WorkoutSession(
                on=entry.on,
                label=entry.label,
                phase=entry.phase,
                day=entry.day,
                template=templates.get((entry.phase, entry.day)),
                note=entry.note,
                program_id=pid,
            )
    return None


def program_summary(
    program_id: str | None = None,
    anchor: date | str | None = None,
    start_day: str | None = None,
) -> dict[str, Any]:
    pid = resolve_program_id(program_id)
    meta = get_program_meta(pid)
    templates, _ = load_program(pid)
    anchor_d, start, calendar = resolve_schedule(pid, anchor, start_day)
    return {
        "program_id": pid,
        "title": meta["title"],
        "short": meta["short"],
        "note_prefix": meta["note_prefix"],
        "path": meta["path"],
        "phases": len({t.phase for t in templates.values()}),
        "templates": len(templates),
        "calendar_days": len(calendar),
        "start": calendar[0].on.isoformat() if calendar else None,
        "end": calendar[-1].on.isoformat() if calendar else None,
        "schedule_anchor": anchor_d.isoformat(),
        "schedule_start_day": start,
        "slot_weekdays": list(PROGRAM_REGISTRY[pid].get("slot_weekdays", SLOT_WEEKDAYS)),
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
        "is_time_hold": ex.is_time_hold,
        "hold_seconds": ex.hold_seconds,
    }


def session_to_dict(session: WorkoutSession | None) -> dict[str, Any] | None:
    if not session:
        return None
    tpl = session.template
    return {
        "program_id": session.program_id,
        "on": session.on.isoformat(),
        "label": session.label,
        "phase": session.phase,
        "day": session.day,
        "note": session.note,
        "title": tpl.title if tpl else None,
        "meta": tpl.meta if tpl else {},
        "exercises": [_exercise_to_dict(ex) for ex in (tpl.exercises if tpl else [])],
    }


def calendar_to_dict(
    program_id: str | None = None,
    anchor: date | str | None = None,
    start_day: str | None = None,
) -> list[dict[str, Any]]:
    return [
        {
            "on": e.on.isoformat(),
            "label": e.label,
            "phase": e.phase,
            "day": e.day,
            "note": e.note,
        }
        for e in get_calendar(program_id, anchor, start_day)
    ]
