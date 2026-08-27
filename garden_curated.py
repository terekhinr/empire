"""Курированные посты Garden (Степаныч) без LLM."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_DATA_PATH = _ROOT / "data" / "garden_curated.json"
_HISTORY_PATH = _ROOT / "data" / "garden_curated_used.json"
_COOLDOWN_DAYS = 21


def _load_entries() -> list[dict]:
    if not _DATA_PATH.is_file():
        return []
    data = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    return list(data.get("entries") or [])


def _load_history() -> dict:
    if not _HISTORY_PATH.is_file():
        return {}
    try:
        return json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_history(data: dict) -> None:
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pick_entry() -> dict | None:
    entries = _load_entries()
    if not entries:
        return None
    used = _load_history()
    last_by_id: dict = dict(used.get("last_by_id") or {})
    now = datetime.utcnow()
    cooldown = timedelta(days=_COOLDOWN_DAYS)

    def eligible(e: dict) -> bool:
        eid = e.get("id")
        if not eid:
            return False
        ts = last_by_id.get(eid)
        if not ts:
            return True
        try:
            return now - datetime.fromisoformat(ts.replace("Z", "")) >= cooldown
        except ValueError:
            return True

    pool = [e for e in entries if eligible(e)] or entries
    # сезон: если указан months — предпочесть текущий месяц
    month = now.month
    seasonal = [e for e in pool if not e.get("months") or month in (e.get("months") or [])]
    chosen = (seasonal or pool)[0]
    return chosen


def mark_used(entry_id: str) -> None:
    used = _load_history()
    last = dict(used.get("last_by_id") or {})
    last[entry_id] = datetime.utcnow().isoformat() + "Z"
    used["last_by_id"] = last
    used["last"] = entry_id
    _save_history(used)


def format_post(entry: dict) -> tuple[str, str]:
    topic = entry.get("topic_raw") or f"[Степаныч] {entry.get('headline') or entry.get('id')}"
    body = (entry.get("body_html") or "").strip()
    tags = (entry.get("hashtags") or "#сад #степаныч").strip()
    if tags and tags not in body:
        body = f"{body}\n\n{tags}"
    return topic, body


def image_rel_path(entry: dict) -> str | None:
    raw = (entry.get("image_file") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_file():
        return str(p.relative_to(_ROOT)) if p.is_absolute() else raw
    rel = _ROOT / raw
    return raw if rel.is_file() else None


def fal_image_prompt(entry: dict) -> str:
    """Английский промпт для fal/flux — дачный/огородный сюжет по теме поста."""
    custom = (entry.get("image_prompt_en") or "").strip()
    if custom:
        return custom
    headline = (entry.get("headline") or entry.get("id") or "garden plot").strip()
    return (
        f"Russian dacha garden, midsummer, {headline}, realistic documentary photo, "
        f"natural daylight, soil plants tools, no text no watermark no logo"
    )


def build_garden_curated_post() -> tuple[str, str, str | None, dict | None]:
    """(topic, text, image_path|None, seed). Без картинки на диске — seed для fal в main."""
    entry = pick_entry()
    if not entry:
        return (
            "[SPECIAL:garden_curated]",
            "🛑 Нет постов в <code>data/garden_curated.json</code>.",
            None,
            None,
        )
    topic, text = format_post(entry)
    eid = entry.get("id")
    if eid:
        mark_used(str(eid))
    img = image_rel_path(entry)
    seed = {
        "_kind": "garden_curated",
        "entry_id": eid,
        "image_prompt_en": fal_image_prompt(entry),
    }
    return topic, text, img, seed
