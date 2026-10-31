"""Публичная лента сайта из очереди издательства."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from publisher.store import Store

MSK = ZoneInfo("Europe/Moscow")


def site_feed(store: Store, project_id: str, *, include_test: bool = False) -> list[dict[str, Any]]:
    data = store.load()
    ok = {"published"}
    if include_test:
        ok.add("test_sent")
    rows = []
    for p in data.get("posts") or []:
        if p.get("project_id") != project_id:
            continue
        if p.get("status") not in ok:
            continue
        rows.append(p)
    rows.sort(key=lambda p: p.get("published_at") or p.get("scheduled_at") or "", reverse=True)
    return rows


def parse_when(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(raw[: len("2026-01-01T00:00:00") if "T" in raw else 16], fmt.replace("%z", ""))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=MSK)
            return dt
        except ValueError:
            continue
    return None
