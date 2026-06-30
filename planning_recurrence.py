"""Task recurrence rules (TickTick / Obsidian compatible subset)."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

REPEAT_OBS_RE = re.compile(r"🔁\s*(.+)$", re.UNICODE)


def serialize_repeat_rule(rule: dict[str, Any] | str | None) -> str | None:
    if rule is None:
        return None
    if isinstance(rule, str):
        return rule.strip() or None
    return json.dumps(rule, ensure_ascii=False)


def parse_repeat_rule(raw: str | dict[str, Any] | None) -> dict[str, Any] | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        return raw
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def repeat_label(rule: dict[str, Any] | None) -> str:
    if not rule:
        return ""
    freq = rule.get("freq") or rule.get("type") or "repeat"
    interval = int(rule.get("interval") or 1)
    if freq == "daily":
        return "каждый день" if interval == 1 else f"каждые {interval} дн."
    if freq == "weekly":
        days = rule.get("byweekday") or rule.get("days")
        if days:
            return f"еженед. ({','.join(str(d) for d in days)})"
        return "еженедельно" if interval == 1 else f"каждые {interval} нед."
    if freq == "monthly":
        return "ежемесячно" if interval == 1 else f"каждые {interval} мес."
    return str(freq)


def extract_obsidian_repeat(line: str) -> tuple[str, dict[str, Any] | None]:
    m = REPEAT_OBS_RE.search(line)
    if not m:
        return line, None
    text = m.group(1).strip().lower()
    cleaned = REPEAT_OBS_RE.sub("", line).strip()
    if text in ("every day", "daily", "каждый день"):
        return cleaned, {"freq": "daily", "interval": 1}
    if text.startswith("every week") or text == "weekly":
        return cleaned, {"freq": "weekly", "interval": 1}
    if text.startswith("every month") or text == "monthly":
        return cleaned, {"freq": "monthly", "interval": 1}
    return cleaned, {"freq": "custom", "label": text}


def _parse_date(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return date.fromisoformat(d[:10])
    except ValueError:
        return None


def next_occurrence(
    due_date: str | None,
    due_time: str | None,
    rule: dict[str, Any] | None,
) -> tuple[str, str | None] | None:
    if not rule:
        return None
    base = _parse_date(due_date) or date.today()
    interval = max(1, int(rule.get("interval") or 1))
    freq = rule.get("freq") or rule.get("type")
    if freq == "daily":
        nxt = base + timedelta(days=interval)
    elif freq == "weekly":
        nxt = base + timedelta(weeks=interval)
    elif freq == "monthly":
        month = base.month - 1 + interval
        year = base.year + month // 12
        month = month % 12 + 1
        day = min(base.day, 28)
        nxt = date(year, month, day)
    else:
        return None
    return nxt.isoformat(), due_time
