"""Идempotency: один слот матрицы (persona × день × HH:MM) — один черновик в сутки."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

_MSK = ZoneInfo("Europe/Moscow")
_STATE_PATH = Path(__file__).resolve().parent / "data" / "scheduler_slots_fired.json"
_RETAIN_DAYS = 14


def _load() -> dict:
    if _STATE_PATH.is_file():
        try:
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"fired": {}}


def _save(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(_MSK).isoformat()
    _STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def slot_key(persona: str, when: datetime, time_str: str) -> str:
    return f"{when.strftime('%Y-%m-%d')}|{persona}|{time_str}"


def _prune(fired: dict) -> dict:
    cutoff = (datetime.now(_MSK).date() - timedelta(days=_RETAIN_DAYS)).isoformat()
    return {k: v for k, v in fired.items() if k.split("|", 1)[0] >= cutoff}


def already_fired(persona: str, when: datetime, time_str: str) -> bool:
    state = _load()
    fired = state.get("fired") or {}
    return slot_key(persona, when, time_str) in fired


def mark_fired(
    persona: str,
    when: datetime,
    time_str: str,
    *,
    draft_id: int | None = None,
    topic: str = "",
) -> None:
    state = _load()
    fired = _prune(state.get("fired") or {})
    key = slot_key(persona, when, time_str)
    fired[key] = {
        "draft_id": draft_id,
        "topic": (topic or "")[:200],
        "at": when.isoformat(),
    }
    state["fired"] = fired
    _save(state)
