"""Curated-рубрики Гдепар из книг (OCR → JSON → пост без LLM)."""

from __future__ import annotations

import json
import random
import re
from datetime import datetime, timedelta
from pathlib import Path

import rubric_posts

_ROOT = Path(__file__).resolve().parent
_EXCERPTS_PATH = _ROOT / "data" / "gdepar_book_excerpts.json"
_CATALOG_PATH = _ROOT / "data" / "gdepar_books_catalog.json"
_HISTORY_PATH = _ROOT / "data" / "gdepar_book_excerpts_used.json"
_MEDIA_DIR = _ROOT / "media" / "gdepar" / "books"

BOOK_RUBRIC_TAGS = {
    "pechi_banya": "[Печь и баня]",
    "istoriya_bani": "[История бани]",
    "zdorovje_par": "[Баня и здоровье]",
}

_COOLDOWN_DAYS = 45


def _load_excerpts() -> dict:
    if not _EXCERPTS_PATH.is_file():
        return {"rubrics": {}, "entries": []}
    return json.loads(_EXCERPTS_PATH.read_text(encoding="utf-8"))


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


def pick_book_entry(rubric_key: str) -> dict | None:
    data = _load_excerpts()
    entries = [
        e
        for e in data.get("entries", [])
        if (e.get("rubric") or "").strip() == rubric_key
    ]
    if not entries:
        return None
    used = _load_history()
    last_by_id: dict = dict(used.get("last_by_id") or {})
    now = datetime.utcnow()
    pool = []
    for e in entries:
        eid = e.get("id")
        if not eid:
            continue
        last = last_by_id.get(eid)
        if not last:
            pool.append(e)
            continue
        try:
            dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if (now - dt.replace(tzinfo=None)) >= timedelta(days=_COOLDOWN_DAYS):
                pool.append(e)
        except ValueError:
            pool.append(e)
    if not pool:
        pool = list(entries)
    entry = random.choice(pool)
    eid = entry.get("id")
    if eid:
        last_by_id[eid] = now.isoformat()
        used["last_by_id"] = last_by_id
        used["last"] = now.isoformat()
        _save_history(used)
    return entry


def format_book_post(entry: dict, rubric_key: str) -> str:
    data = _load_excerpts()
    meta = (data.get("rubrics") or {}).get(rubric_key) or {}
    title = meta.get("title", rubric_key)
    emoji = meta.get("emoji", "📚")
    tag = entry.get("tag") or meta.get("hashtag", "книга")
    source = f"{entry.get('author', '')}, {entry.get('work', '')}"
    if entry.get("chapter"):
        source += f" · {entry['chapter']}"
    payload = {
        **entry,
        "source": source.strip(" ,"),
        "text": entry.get("quote") or entry.get("text", ""),
    }
    return rubric_posts.format_curated_post(
        title,
        emoji,
        payload,
        hashtags=f"#баня #гдепар #{tag} #книга",
        source_label=meta.get("source_label", "Книга"),
        commentary_prefix="💬 <b>Михалыч:</b>",
        show_commentary=bool(entry.get("note")),
    )


async def build_book_rubric_post(rubric_key: str) -> tuple[str, str | None, str | None]:
    """(topic_raw, html, image_path)."""
    tag = BOOK_RUBRIC_TAGS.get(rubric_key, "[Книга]")
    entry = pick_book_entry(rubric_key)
    if not entry:
        body = (
            f"📚 <b>{tag.strip('[]')}</b>\n\n"
            "Выпусков из книги пока нет — добавьте фрагменты через "
            "<code>tools/build_gdepar_book_excerpts.py</code>.\n\n"
            "#баня #гдепар #книга"
        )
        return f"{tag} fallback", body, None
    topic = (
        f"{tag} {entry.get('author', '')}, {entry.get('work', '')} "
        f"(id={entry.get('id', '')})"
    )
    text = format_book_post(entry, rubric_key)
    data = _load_excerpts()
    meta = (data.get("rubrics") or {}).get(rubric_key) or {}
    if meta.get("image_file"):
        entry = {**entry, "image_file": meta["image_file"]}
    img = await rubric_posts.ensure_entry_image(entry, _MEDIA_DIR, "_default_gdepar_book.jpg")
    return topic, text, img


def is_book_rubric_slot(slot_value) -> str | None:
    """Возвращает rubric_key или None."""
    if not isinstance(slot_value, dict):
        return None
    t = (slot_value.get("type") or slot_value.get("special") or "").strip().lower()
    if t not in ("book_rubric", "gdepar_book", "[special:book_rubric]"):
        return None
    key = (slot_value.get("rubric") or slot_value.get("book") or "").strip()
    return key or None
