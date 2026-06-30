"""Calendar and ICS parsing tests."""

from __future__ import annotations

from datetime import date

from planning_calendar import calendar_payload, parse_ics_events


SAMPLE_ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:test1
SUMMARY:Встреча
DTSTART;VALUE=DATE:20260624
DTEND;VALUE=DATE:20260625
END:VEVENT
BEGIN:VEVENT
UID:test2
SUMMARY:Звонок
DTSTART:20260626T100000Z
DTEND:20260626T110000Z
END:VEVENT
END:VCALENDAR
"""


def test_parse_ics_events():
    events = parse_ics_events(SAMPLE_ICS)
    assert len(events) == 2
    assert events[0]["title"] == "Встреча"
    assert events[0]["start"] == "2026-06-24"
    assert events[0]["all_day"] is True
    assert events[1]["source"] == "google"


def test_calendar_payload_tasks_only(monkeypatch):
    monkeypatch.setattr(
        "planning_calendar.list_tasks",
        lambda **_: [
            {"id": 1, "title": "A", "due_date": "2026-06-24", "status": "todo"},
            {"id": 2, "title": "B", "due_date": "2026-07-01", "status": "todo"},
        ],
    )
    monkeypatch.setattr("planning_calendar.get_google_ical_url", lambda: "")
    payload = calendar_payload(date(2026, 6, 1), date(2026, 6, 30))
    assert len(payload["tasks"]) == 1
    assert payload["google_configured"] is False
