"""Task calendar + Google Calendar (iCal URL) for Empire Tasks PWA."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from planning_db import get_planning_setting, list_tasks, set_planning_setting

GOOGLE_ICAL_KEY = "google_ical_url"
_ICAL_FETCH_TIMEOUT = 20


def get_google_ical_url() -> str:
    return get_planning_setting(GOOGLE_ICAL_KEY, "").strip()


def set_google_ical_url(url: str | None) -> None:
    set_planning_setting(GOOGLE_ICAL_KEY, (url or "").strip())


def _unfold_ics(raw: str) -> list[str]:
    lines: list[str] = []
    for line in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith((" ", "\t")) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def _parse_ics_datetime(value: str, params: str) -> tuple[str, bool]:
    val = value.strip()
    if "VALUE=DATE" in params.upper() and len(val) >= 8:
        d = f"{val[:4]}-{val[4:6]}-{val[6:8]}"
        return d, True
    if len(val) >= 8 and val[8:9] in ("T", "t"):
        try:
            if val.endswith("Z"):
                dt = datetime.strptime(val, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            else:
                dt = datetime.strptime(val[:15], "%Y%m%dT%H%M%S")
            return dt.date().isoformat(), False
        except ValueError:
            pass
    if len(val) >= 8:
        return f"{val[:4]}-{val[4:6]}-{val[6:8]}", True
    return val, True


def parse_ics_events(raw: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    block: list[str] = []
    in_event = False
    for line in _unfold_ics(raw):
        upper = line.upper()
        if upper == "BEGIN:VEVENT":
            in_event = True
            block = []
            continue
        if upper == "END:VEVENT":
            in_event = False
            ev = _event_from_block(block)
            if ev:
                events.append(ev)
            continue
        if in_event:
            block.append(line)
    return events


def _event_from_block(lines: list[str]) -> dict[str, Any] | None:
    title = ""
    start = ""
    end = ""
    all_day = True
    uid = ""
    for line in lines:
        if line.startswith("SUMMARY"):
            title = line.split(":", 1)[1].strip()
        elif line.startswith("UID"):
            uid = line.split(":", 1)[1].strip()
        elif line.startswith("DTSTART"):
            params, _, value = line.partition(":")
            start, all_day = _parse_ics_datetime(value, params)
        elif line.startswith("DTEND"):
            params, _, value = line.partition(":")
            end, _ = _parse_ics_datetime(value, params)
    if not title or not start:
        return None
    if not end:
        end = start
    return {
        "id": uid or f"gcal-{title}-{start}",
        "title": title,
        "start": start,
        "end": end,
        "all_day": all_day,
        "source": "google",
    }


def fetch_google_ical_events(url: str, *, from_date: date, to_date: date) -> list[dict[str, Any]]:
    if not url.strip():
        return []
    req = Request(url.strip(), headers={"User-Agent": "Empire-Tasks/1.0"})
    with urlopen(req, timeout=_ICAL_FETCH_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    out: list[dict[str, Any]] = []
    for ev in parse_ics_events(raw):
        start = ev["start"]
        end = ev.get("end") or start
        if start > to_date.isoformat() or end < from_date.isoformat():
            continue
        out.append(ev)
    out.sort(key=lambda e: (e["start"], e["title"]))
    return out


def tasks_in_range(from_date: date, to_date: date) -> list[dict[str, Any]]:
    start = from_date.isoformat()
    end = to_date.isoformat()
    items = list_tasks(include_done=False, limit=2000)
    return [
        t
        for t in items
        if t.get("due_date") and start <= t["due_date"] <= end and t.get("status") not in ("done", "cancelled")
    ]


def calendar_payload(from_date: date, to_date: date) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "tasks": tasks_in_range(from_date, to_date),
        "google_events": [],
        "google_configured": False,
        "google_error": None,
    }
    url = get_google_ical_url()
    if not url:
        return payload
    payload["google_configured"] = True
    try:
        payload["google_events"] = fetch_google_ical_events(url, from_date=from_date, to_date=to_date)
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        payload["google_error"] = str(exc)
    return payload
