"""Ручные посты Михалыч ↔ Кириллыч для Гдепар (без LLM, как «Классическая баня»)."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import rubric_posts

_ROOT = Path(__file__).resolve().parent
_DATA_PATH = _ROOT / "data" / "gdepar_duo_curated.json"
_HISTORY_PATH = _ROOT / "data" / "gdepar_duo_curated_used.json"
_MEDIA_DIR = _ROOT / "media" / "gdepar" / "duo"

DUO_RUBRIC_TAG = "[Дуэт]"
_COOLDOWN_DAYS = 42


def _load_data() -> dict:
    if not _DATA_PATH.is_file():
        return {"entries": []}
    return json.loads(_DATA_PATH.read_text(encoding="utf-8"))


def _load_history() -> dict:
    if not _HISTORY_PATH.is_file():
        return {}
    try:
        return json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_history(data: dict) -> None:
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_entry(*, pool: str | None = None) -> dict | None:
    entries = _load_data().get("entries") or []
    if pool:
        filtered = [e for e in entries if (e.get("pool") or "any") == pool]
        if not filtered:
            return None
        entries = filtered
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

    pool_eligible = [e for e in entries if eligible(e)]
    if not pool_eligible:
        pool_eligible = list(entries)
    entry = random.choice(pool_eligible)
    eid = entry.get("id")
    if eid:
        last_by_id[eid] = now.isoformat()
        used["last_by_id"] = last_by_id
        used["last"] = now.isoformat()
        _save_history(used)
    return entry


def format_post(entry: dict) -> str:
    if entry.get("body_html"):
        return entry["body_html"].strip()
    headline = entry.get("headline") or "Баня"
    tag = entry.get("tag", "гдепар")
    lines = [f"🔥 <b>{headline}</b>", ""]
    for block in entry.get("lines") or []:
        who = (block.get("who") or "mikhalych").lower()
        label = "Михалыч" if who.startswith("м") else "Кириллыч"
        text = (block.get("text") or "").strip()
        if text:
            lines.append(f"<b>{label}:</b> {text}")
            lines.append("")
    tags = (entry.get("hashtags") or "").strip()
    if tags:
        if not tags.startswith("#"):
            tags = " ".join(f"#{t.lstrip('#')}" for t in tags.split())
        lines.append(tags)
    else:
        lines.append(f"#баня #гдепар #{tag}")
    return "\n".join(lines).strip()


def image_rel_path(entry: dict) -> str | None:
    raw = (entry.get("image_file") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_file():
        return str(p.relative_to(_ROOT)) if p.is_absolute() else raw
    rel = _ROOT / raw
    return raw if rel.is_file() else None


async def build_duo_curated_slot(*, pool: str | None = None) -> tuple[str, str | None, str | None]:
    """(topic_raw, prebuilt_html, image_path) — без LLM."""
    entry = pick_entry(pool=pool)
    if not entry:
        body = (
            f"{DUO_RUBRIC_TAG}\n\n"
            "Очередь ручных постов пуста — добавьте выпуски в "
            "<code>data/gdepar_duo_curated.json</code> "
            "(см. <code>docs/gdepar_duo_curated.md</code>)."
        )
        return f"{DUO_RUBRIC_TAG} fallback pool={pool or 'any'}", body, None

    eid = entry["id"]
    topic = f"{DUO_RUBRIC_TAG} {entry.get('headline', eid)} (id={eid})"
    body = format_post(entry)
    img = image_rel_path(entry)
    return topic, body, img


def is_duo_curated_slot(slot_value) -> bool:
    if isinstance(slot_value, dict):
        t = slot_value.get("type") or slot_value.get("special")
        return t in ("duo_curated", "duo", "[SPECIAL:duo_curated]")
    return False


def pool_from_slot(slot_value) -> str | None:
    if isinstance(slot_value, dict):
        return slot_value.get("pool")
    return None
