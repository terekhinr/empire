"""Курированные посты Stern (09:30 / 19:00) без LLM."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_DATA_PATH = _ROOT / "data" / "stern_curated.json"
_HISTORY_PATH = _ROOT / "data" / "stern_curated_used.json"
_COOLDOWN_DAYS = 28
# Совпадает с data/auto_publish.json → rubrics.stern_matrix_curated.min_body_chars
_MIN_BODY_CHARS = 220

CURATED_TAG = "[Stern curated]"


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
    if not _image_exists(e):
        return False
    body = (e.get("body_html") or "").strip()
    if not body:
        return False
    return _body_len(body) >= _MIN_BODY_CHARS


def pick_entry(*, slot: str) -> dict | None:
    entries = _load_data().get("entries") or []
    filtered = [
        e
        for e in entries
        if str(e.get("slot") or "") == slot and _publishable(e)
    ]
    if not filtered:
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

    pool = [e for e in filtered if eligible(e)] or list(filtered)
    entry = random.choice(pool)
    eid = entry.get("id")
    if eid:
        last_by_id[eid] = now.isoformat()
        used["last_by_id"] = last_by_id
        used["last"] = now.isoformat()
        _save_history(used)
    return entry


def is_stern_curated_slot(slot_value) -> bool:
    if isinstance(slot_value, dict):
        t = slot_value.get("type") or slot_value.get("special")
        return t in ("stern_curated", "[SPECIAL:stern_curated]")
    return False


def slot_from_value(slot_value) -> str:
    if isinstance(slot_value, dict):
        return str(slot_value.get("slot") or "0930")
    return "0930"


def image_rel_path(entry: dict) -> str | None:
    raw = (entry.get("image_file") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_file():
        return str(p.relative_to(_ROOT)) if p.is_absolute() else raw
    rel = _ROOT / raw
    return raw if rel.is_file() else None


async def build_stern_curated_slot(*, slot: str = "0930") -> tuple[str, str | None, str | None, dict | None]:
    entry = pick_entry(slot=slot)
    if not entry:
        topic = f"{CURATED_TAG} slot={slot}"
        body = (
            f"🛑 <b>Очередь Stern {slot} пуста</b>\n\n"
            "Добавьте посты в Gemini → ingest → "
            "<code>parse_stern_curated_import.py</code>."
        )
        return topic, body, None, None
    topic = entry.get("topic_raw") or f"{CURATED_TAG} {entry.get('id')}"
    body = (entry.get("body_html") or "").strip()
    img = image_rel_path(entry)
    seed = {
        "_kind": "stern_curated",
        "image_prompt_en": entry.get("image_prompt_en") or "",
        "entry_id": entry.get("id"),
    }
    return topic, body, img, seed
