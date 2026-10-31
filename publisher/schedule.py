"""Слоты и календарь: назначить пост в ближайшее свободное окно."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from publisher.catalog import WEEKDAYS_RU, project_by_id

MSK = ZoneInfo("Europe/Moscow")


def parse_hhmm(raw: str) -> tuple[int, int] | None:
    s = (raw or "").strip()
    parts = s.split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if 0 <= h <= 23 and 0 <= m <= 59:
        return h, m
    return None


def format_hhmm(raw: str) -> str:
    hm = parse_hhmm(raw)
    if not hm:
        return (raw or "").strip()
    return f"{hm[0]:02d}:{hm[1]:02d}"


def next_datetime_for_slot(
    weekday: int,
    time_s: str,
    *,
    after: datetime,
    allow_same: bool = True,
) -> datetime | None:
    """Ближайшая дата слота (МСК) строго после `after`, либо в тот же слот если allow_same и ещё не прошёл."""
    hm = parse_hhmm(time_s)
    if hm is None or not (0 <= weekday <= 6):
        return None
    now = after.astimezone(MSK)
    h, m = hm
    # Python weekday: Mon=0
    days_ahead = (weekday - now.weekday()) % 7
    candidate = now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=days_ahead)
    if days_ahead == 0:
        if candidate < now or (candidate == now and not allow_same):
            candidate += timedelta(days=7)
        elif candidate == now and allow_same:
            pass
        elif candidate < now:
            candidate += timedelta(days=7)
    if candidate < now:
        candidate += timedelta(days=7)
    return candidate


def occupied_keys(posts: list[dict], *, ignore_id: str | None = None) -> set[tuple[str, str]]:
    """(project_id, scheduled_at) занятые слоты."""
    busy: set[tuple[str, str]] = set()
    for p in posts:
        if ignore_id and p.get("id") == ignore_id:
            continue
        if p.get("status") in ("cancelled", "failed"):
            continue
        sched = p.get("scheduled_at")
        pid = p.get("project_id")
        if sched and pid:
            busy.add((pid, sched))
    return busy


def enabled_slots(slots: list[dict], project_id: str | None = None) -> list[dict]:
    out = []
    for s in slots:
        if not s.get("enabled", True):
            continue
        if project_id and s.get("project_id") != project_id:
            continue
        out.append(s)
    return sorted(out, key=lambda s: (s.get("weekday", 0), s.get("time") or ""))


def assign_next_slots(
    entries: list[dict],
    slots: list[dict],
    posts: list[dict],
    *,
    after: datetime | None = None,
    default_project: str | None = None,
) -> list[dict]:
    """Проставляет scheduled_at на ближайшие свободные слоты. Не мутирует store."""
    now = after or datetime.now(MSK)
    busy = occupied_keys(posts)
    assigned: list[dict] = []

    for entry in entries:
        item = dict(entry)
        pid = item.get("project_id") or default_project
        if not pid or project_by_id(pid) is None:
            item["error"] = "unknown_project"
            assigned.append(item)
            continue
        item["project_id"] = pid
        if item.get("scheduled_at"):
            busy.add((pid, item["scheduled_at"]))
            assigned.append(item)
            continue

        slot_time = format_hhmm(item.get("slot_time") or "") or None
        weekday = item.get("weekday")
        candidates = enabled_slots(slots, pid)
        if weekday is not None and slot_time:
            candidates = [
                s
                for s in candidates
                if s.get("weekday") == weekday and format_hhmm(s.get("time") or "") == slot_time
            ] or candidates
        elif slot_time:
            candidates = [s for s in candidates if format_hhmm(s.get("time") or "") == slot_time] or candidates
        elif weekday is not None:
            candidates = [s for s in candidates if s.get("weekday") == weekday] or candidates

        chosen = None
        chosen_dt = None
        for s in candidates:
            dt = next_datetime_for_slot(int(s["weekday"]), s.get("time") or "", after=now, allow_same=True)
            if dt is None:
                continue
            key = (pid, dt.strftime("%Y-%m-%d %H:%M"))
            # Если занято — ищем +7 дней пока не свободно (до 12 недель)
            hops = 0
            while key in busy and hops < 12:
                dt = dt + timedelta(days=7)
                key = (pid, dt.strftime("%Y-%m-%d %H:%M"))
                hops += 1
            if key in busy:
                continue
            if chosen_dt is None or dt < chosen_dt:
                chosen = s
                chosen_dt = dt
        if chosen is None or chosen_dt is None:
            item["error"] = "no_free_slot"
            assigned.append(item)
            continue
        stamp = chosen_dt.strftime("%Y-%m-%d %H:%M")
        item["scheduled_at"] = stamp
        item["slot_id"] = chosen.get("id")
        item.pop("error", None)
        busy.add((pid, stamp))
        assigned.append(item)
    return assigned


def week_grid(
    slots: list[dict],
    posts: list[dict],
    *,
    week_start: datetime,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Сетка Пн–Вс текущей недели для UI."""
    start = week_start.astimezone(MSK).replace(hour=0, minute=0, second=0, microsecond=0)
    start -= timedelta(days=start.weekday())
    days = []
    for i in range(7):
        day = start + timedelta(days=i)
        days.append(
            {
                "weekday": i,
                "label": WEEKDAYS_RU[i],
                "date": day.strftime("%Y-%m-%d"),
                "date_ru": day.strftime("%d.%m"),
            }
        )
    slot_rows: dict[str, None] = {}
    for s in enabled_slots(slots, project_id):
        t = format_hhmm(s.get("time") or "")
        if t:
            slot_rows[t] = None
    times = sorted(slot_rows.keys())

    cells: dict[str, list[dict]] = {}
    for d in days:
        for t in times:
            cells[f"{d['date']} {t}"] = []

    week_end = start + timedelta(days=7)
    for p in posts:
        if p.get("status") == "cancelled":
            continue
        if project_id and p.get("project_id") != project_id:
            continue
        sched = p.get("scheduled_at") or ""
        if len(sched) < 16:
            continue
        try:
            dt = datetime.strptime(sched[:16], "%Y-%m-%d %H:%M").replace(tzinfo=MSK)
        except ValueError:
            continue
        if not (start <= dt < week_end):
            continue
        key = dt.strftime("%Y-%m-%d %H:%M")
        cells.setdefault(key, []).append(
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "status": p.get("status"),
                "project_id": p.get("project_id"),
            }
        )

    return {
        "week_start": start.strftime("%Y-%m-%d"),
        "week_end": (start + timedelta(days=6)).strftime("%Y-%m-%d"),
        "days": days,
        "times": times,
        "cells": cells,
        "slots": [s for s in enabled_slots(slots, project_id)],
    }
