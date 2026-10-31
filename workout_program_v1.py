"""Canonical workout program file: empire-workout-program/v1 (JSON or YAML)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "empire-workout-program/v1"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
DAY_LETTERS = ("A", "B", "C", "D", "E", "F", "G")
WEEKDAY_NAMES = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
    "пн": 0,
    "вт": 1,
    "ср": 2,
    "чт": 3,
    "пт": 4,
    "сб": 5,
    "вс": 6,
}
RESERVED_IDS = frozenset({"gym_2026", "outside_hall"})


class ProgramFileError(ValueError):
    pass


def slugify_id(raw: str) -> str:
    text = (raw or "").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if text and text[0].isdigit():
        text = f"p_{text}"
    if not ID_RE.match(text):
        raise ProgramFileError(f"invalid_program_id:{raw}")
    return text


def parse_weekdays(raw: Any) -> list[int]:
    if raw is None:
        return [0, 2, 4]
    if not isinstance(raw, list) or not raw:
        raise ProgramFileError("weekdays_must_be_non_empty_list")
    out: list[int] = []
    for item in raw:
        if isinstance(item, int) and 0 <= item <= 6:
            out.append(item)
            continue
        if isinstance(item, str):
            key = item.strip().lower()
            if key.isdigit():
                n = int(key)
                if 0 <= n <= 6:
                    out.append(n)
                    continue
            if key in WEEKDAY_NAMES:
                out.append(WEEKDAY_NAMES[key])
                continue
        raise ProgramFileError(f"invalid_weekday:{item}")
    seen: list[int] = []
    for d in out:
        if d not in seen:
            seen.append(d)
    return seen


def _as_range(value: Any) -> tuple[float | None, float | None, float | None]:
    if value is None or value == "":
        return None, None, None
    if isinstance(value, (int, float)):
        n = float(value)
        return n, n, n
    if isinstance(value, list) and len(value) == 2:
        lo, hi = float(value[0]), float(value[1])
        return round((lo + hi) / 2, 1), lo, hi
    raise ProgramFileError(f"invalid_numeric_range:{value}")


def _prescription(ex: dict[str, Any]) -> str:
    sets = int(ex.get("sets") or 0)
    if ex.get("is_max") or str(ex.get("reps")).lower() in ("max", "макс"):
        return f"{max(sets, 1)}×МАКС"
    reps = ex.get("reps")
    if isinstance(reps, list) and len(reps) == 2:
        return f"{sets}×{int(reps[0])}–{int(reps[1])}"
    if reps is not None and reps != "":
        return f"{sets}×{int(float(reps))}"
    hold = ex.get("hold_sec")
    if hold:
        return f"{max(sets, 1)}×{int(hold)} сек"
    return f"{sets}×0"


def normalize_exercise(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ProgramFileError("exercise_must_be_object")
    key = str(raw.get("key") or raw.get("exercise_key") or "").strip()
    if not key:
        raise ProgramFileError("exercise_key_required")
    name = str(raw.get("name") or raw.get("label") or "").strip()
    sets = int(raw.get("sets") or 0)
    reps_raw = raw.get("reps")
    is_max = bool(raw.get("is_max")) or str(reps_raw).lower() in ("max", "макс")
    reps = rmin = rmax = None
    if not is_max:
        mid, lo, hi = _as_range(reps_raw if not isinstance(reps_raw, str) else None)
        if isinstance(reps_raw, str) and reps_raw.strip() and not is_max:
            digits = re.findall(r"\d+", reps_raw)
            if len(digits) >= 2:
                lo, hi = float(digits[0]), float(digits[1])
                mid = (lo + hi) / 2
            elif digits:
                mid = lo = hi = float(digits[0])
        reps = int(mid) if mid is not None else None
        rmin = int(lo) if lo is not None else None
        rmax = int(hi) if hi is not None else None
    w_mid, _, _ = _as_range(raw.get("weight_kg"))
    hold = raw.get("hold_sec") or raw.get("hold_seconds")
    hold_i = int(hold) if hold not in (None, "") else None
    is_time_hold = bool(raw.get("is_time_hold"))
    if hold_i and sets and (reps is None or (reps and reps >= 30)) and "планка" in key.lower():
        is_time_hold = True
    notes = str(raw.get("notes") or raw.get("detail") or "").strip()
    rest = raw.get("rest_sec")
    if rest:
        notes = (notes + f" | отдых {int(rest)} сек").strip(" |")
    return {
        "key": key,
        "name": name,
        "sets": sets,
        "reps": reps,
        "reps_min": rmin,
        "reps_max": rmax,
        "is_max": is_max,
        "weight_kg": w_mid,
        "hold_sec": hold_i,
        "is_time_hold": is_time_hold,
        "notes": notes,
        "prescription": str(raw.get("prescription") or _prescription({
            "sets": sets,
            "reps": reps_raw if reps_raw is not None else ([rmin, rmax] if rmin and rmax and rmin != rmax else reps),
            "is_max": is_max,
            "hold_sec": hold_i,
        })),
    }


def normalize_spec(raw: dict[str, Any], *, fallback_id: str | None = None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ProgramFileError("root_must_be_object")
    schema = str(raw.get("schema") or SCHEMA).strip()
    if schema != SCHEMA:
        raise ProgramFileError(f"unsupported_schema:{schema}")
    pid = slugify_id(str(raw.get("id") or fallback_id or ""))
    title = str(raw.get("title") or pid).strip()
    short = str(raw.get("short") or title).strip()
    phases_in = raw.get("phases")
    if not isinstance(phases_in, list) or not phases_in:
        raise ProgramFileError("phases_required")
    phases: list[dict[str, Any]] = []
    for i, phase in enumerate(phases_in, start=1):
        if not isinstance(phase, dict):
            raise ProgramFileError("phase_must_be_object")
        phase_id = int(phase.get("id") or i)
        days_in = phase.get("days")
        if not isinstance(days_in, list) or not days_in:
            raise ProgramFileError(f"phase_{phase_id}_days_required")
        days: list[dict[str, Any]] = []
        for j, day in enumerate(days_in):
            if not isinstance(day, dict):
                raise ProgramFileError("day_must_be_object")
            letter = str(day.get("id") or DAY_LETTERS[j % len(DAY_LETTERS)]).strip().upper()
            if letter not in DAY_LETTERS:
                raise ProgramFileError(f"invalid_day_id:{letter}")
            exercises = [normalize_exercise(ex) for ex in (day.get("exercises") or [])]
            if not exercises:
                raise ProgramFileError(f"day_{letter}_exercises_required")
            days.append({
                "id": letter,
                "title": str(day.get("title") or f"День {letter}").strip(),
                "exercises": exercises,
            })
        phases.append({
            "id": phase_id,
            "title": str(phase.get("title") or f"Фаза {phase_id}").strip(),
            "days": days,
        })
    calendar = []
    for row in raw.get("calendar") or []:
        if not isinstance(row, dict):
            continue
        calendar.append({
            "on": str(row["on"]),
            "phase": int(row.get("phase") or 1),
            "day": str(row.get("day") or "A").upper(),
            "note": str(row.get("note") or ""),
        })
    rolling = raw.get("rolling_sessions")
    return {
        "schema": SCHEMA,
        "id": pid,
        "title": title,
        "short": short[:24],
        "author": str(raw.get("author") or "").strip(),
        "note_prefix": str(raw.get("note_prefix") or "подход").strip() or "подход",
        "weekdays": parse_weekdays(raw.get("weekdays")),
        "start": raw.get("start"),
        "rolling_sessions": int(rolling) if rolling else None,
        "phases": phases,
        "calendar": calendar,
    }


def loads(text: str, *, filename: str = "program.json") -> dict[str, Any]:
    name = filename.lower()
    stripped = text.lstrip("\ufeff")
    data: Any
    if name.endswith((".yaml", ".yml")) or (not name.endswith(".json") and stripped.startswith("schema:")):
        import yaml  # type: ignore

        data = yaml.safe_load(stripped)
    else:
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            if name.endswith(".json"):
                raise ProgramFileError(f"invalid_json:{exc}") from exc
            import yaml  # type: ignore

            data = yaml.safe_load(stripped)
    stem = Path(filename).stem
    try:
        fallback_id = slugify_id(stem)
    except ProgramFileError:
        fallback_id = None
    return normalize_spec(data, fallback_id=fallback_id)


def dumps(spec: dict[str, Any]) -> str:
    return json.dumps(normalize_spec(spec), ensure_ascii=False, indent=2) + "\n"


def templates_from_spec(spec: dict[str, Any]) -> dict[tuple[int, str], Any]:
    from health_workout_program import WorkoutDayTemplate, WorkoutExercise

    templates: dict[tuple[int, str], Any] = {}
    for phase in spec["phases"]:
        for day in phase["days"]:
            exercises = []
            for ex in day["exercises"]:
                exercises.append(
                    WorkoutExercise(
                        exercise_key=ex["key"],
                        prescription=ex["prescription"],
                        detail=ex["notes"],
                        sets=ex["sets"],
                        reps=ex["reps"],
                        reps_min=ex["reps_min"],
                        reps_max=ex["reps_max"],
                        is_max=ex["is_max"],
                        suggested_weight_kg=ex["weight_kg"],
                        is_time_hold=ex["is_time_hold"],
                        hold_seconds=ex["hold_sec"],
                    )
                )
            templates[(int(phase["id"]), day["id"])] = WorkoutDayTemplate(
                phase=int(phase["id"]),
                phase_title=phase["title"],
                day=day["id"],
                title=day["title"],
                meta={},
                exercises=exercises,
            )
    return templates


def calendar_from_spec(spec: dict[str, Any]) -> list[Any]:
    from health_workout_program import CalendarEntry
    from datetime import date

    out = []
    for row in spec.get("calendar") or []:
        letter = row["day"]
        phase = int(row["phase"])
        out.append(
            CalendarEntry(
                on=date.fromisoformat(row["on"]),
                label=f"Фаза {phase} / День {letter}",
                phase=phase,
                day=letter,
                note=row.get("note") or "",
            )
        )
    return out


def spec_from_markdown_parse(
    templates: dict,
    calendar: list,
    *,
    program_id: str,
    title: str,
    short: str,
    note_prefix: str = "подход",
    weekdays: list[int] | None = None,
    rolling_sessions: int | None = None,
) -> dict[str, Any]:
    phases_map: dict[int, dict[str, Any]] = {}
    for (phase, letter), tpl in sorted(templates.items()):
        bucket = phases_map.setdefault(phase, {"id": phase, "title": tpl.phase_title, "days": []})
        days = bucket["days"]
        days.append({
            "id": letter,
            "title": tpl.title,
            "exercises": [
                {
                    "key": ex.exercise_key,
                    "name": ex.exercise_label,
                    "sets": ex.sets,
                    "reps": "max" if ex.is_max else (
                        [ex.reps_min, ex.reps_max]
                        if ex.reps_min and ex.reps_max and ex.reps_min != ex.reps_max
                        else ex.reps
                    ),
                    "weight_kg": ex.suggested_weight_kg,
                    "hold_sec": ex.hold_seconds,
                    "is_time_hold": ex.is_time_hold,
                    "notes": ex.detail,
                    "prescription": ex.prescription,
                    "is_max": ex.is_max,
                }
                for ex in tpl.exercises
            ],
        })
    return normalize_spec({
        "schema": SCHEMA,
        "id": program_id,
        "title": title,
        "short": short,
        "note_prefix": note_prefix,
        "weekdays": weekdays or [0, 2, 4],
        "rolling_sessions": rolling_sessions,
        "phases": [phases_map[k] for k in sorted(phases_map)],
        "calendar": [
            {"on": e.on.isoformat(), "phase": e.phase, "day": e.day, "note": e.note}
            for e in calendar
        ],
    })


def register_exercises(spec: dict[str, Any]) -> None:
    from health_db import ensure_exercise

    for phase in spec["phases"]:
        for day in phase["days"]:
            for ex in day["exercises"]:
                ensure_exercise(ex["key"], ex.get("name") or None)
