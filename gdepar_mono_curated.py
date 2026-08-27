"""Ручные монологи Михалыч / Кириллыч для Гдепар (без LLM, без обязательной картинки)."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_DATA_PATH = _ROOT / "data" / "gdepar_mono_curated.json"
_HISTORY_PATH = _ROOT / "data" / "gdepar_mono_curated_used.json"

MONO_RUBRIC_TAG = "[Монолог]"
_COOLDOWN_DAYS = 14
# Совпадает с data/auto_publish.json → rubrics.gdepar_mono_curated.min_body_chars
_MIN_BODY_CHARS = 100


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


def _body_len(text: str) -> int:
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    body = [ln for ln in lines if not ln.lstrip().startswith("#")]
    return len("\n".join(body))


def _image_exists(entry: dict) -> bool:
    raw = (entry.get("image_file") or "").strip()
    if not raw:
        return False
    p = Path(raw)
    if p.is_file():
        return True
    return (_ROOT / raw).is_file()


def _publishable(e: dict) -> bool:
    if e.get("deprecated"):
        return False
    body = (e.get("body_html") or "").strip()
    if not body:
        return False
    if _body_len(body) < _MIN_BODY_CHARS:
        return False
    # Картинка опциональна; если указана — должна существовать.
    raw = (e.get("image_file") or "").strip()
    if raw and not _image_exists(e):
        return False
    return True


def pick_entry(*, pool: str | None = None) -> dict | None:
    entries = _load_data().get("entries") or []
    if pool:
        filtered = [e for e in entries if (e.get("pool") or "any") == pool]
        if not filtered:
            return None
        entries = filtered
    entries = [e for e in entries if _publishable(e)]
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
    voice = (entry.get("voice") or "mikhalych").lower()
    label = "Михалыч" if voice.startswith("m") or voice.startswith("м") else "Кириллыч"
    text = (entry.get("text") or "").strip()
    tag = entry.get("tag") or ("михалыч" if label == "Михалыч" else "кириллыч")
    lines = [f"🔥 <b>{headline}</b>", "", f"<b>{label}:</b> {text}", ""]
    tags = (entry.get("hashtags") or "").strip()
    if tags:
        lines.append(tags if tags.startswith("#") else f"#{tags}")
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


async def build_mono_curated_slot(*, pool: str | None = None) -> tuple[str, str | None, str | None]:
    """(topic_raw, prebuilt_html, image_path) — без LLM."""
    entry = pick_entry(pool=pool)
    if not entry:
        # Fallback: любой пул, затем duo не трогаем — пустой слот с пометкой.
        if pool:
            entry = pick_entry(pool=None)
    if not entry:
        body = (
            f"{MONO_RUBRIC_TAG}\n\n"
            "Очередь монологов пуста — добавьте выпуски в "
            "<code>data/gdepar_mono_curated.json</code>."
        )
        return f"{MONO_RUBRIC_TAG} fallback pool={pool or 'any'}", body, None

    eid = entry["id"]
    topic = f"{MONO_RUBRIC_TAG} {entry.get('headline', eid)} (id={eid})"
    body = format_post(entry)
    img = image_rel_path(entry)
    return topic, body, img


def is_mono_curated_slot(slot_value) -> bool:
    if isinstance(slot_value, dict):
        t = slot_value.get("type") or slot_value.get("special")
        return t in ("mono_curated", "mono", "[SPECIAL:mono_curated]")
    return False


def pool_from_slot(slot_value) -> str | None:
    if isinstance(slot_value, dict):
        return slot_value.get("pool")
    return None
