"""Очередь видео-разборов техники (#161–#200) для слота 15:00 Штерн."""

from __future__ import annotations

import json
from pathlib import Path

import rubric_posts

_ROOT = Path(__file__).resolve().parent
_MATRIX = _ROOT / "data" / "stern_technique_matrix_161_200.json"
_USED = _ROOT / "data" / "stern_technique_used.json"
TOPIC_TAG = "[Техника гирь]"


def load_matrix() -> dict:
    return rubric_posts.load_json(_MATRIX)


def pick_entry() -> dict | None:
    data = load_matrix()
    used = set(rubric_posts.load_json(_USED).get("ids") or [])
    for entry in data.get("entries") or []:
        if entry.get("status") != "ready":
            continue
        eid = entry.get("id")
        if not eid or eid in used:
            continue
        clip = (entry.get("clip_file") or (entry.get("video") or {}).get("subtitled_file") or "").strip()
        if clip and not (_ROOT / clip).is_file():
            continue
        return entry
    return None


def mark_used(entry_id: str) -> None:
    hist = rubric_posts.load_json(_USED)
    ids = list(hist.get("ids") or [])
    if entry_id not in ids:
        ids.append(entry_id)
    hist["ids"] = ids[-120:]
    _USED.parent.mkdir(parents=True, exist_ok=True)
    _USED.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")


def format_post(entry: dict) -> str:
    if entry.get("body_html"):
        return entry["body_html"].strip()
    headline = entry.get("headline") or entry.get("exercise") or "Разбор техники"
    tag = entry.get("tag", "техника")
    lines = [
        f"🏛️ <b>{headline}</b>",
        "",
        f"<b>Упражнение:</b> {entry.get('exercise', '—')}",
        f"<b>Атлет:</b> {entry.get('athlete', '—')}",
        "",
        (entry.get("commentary") or entry.get("video_breakdown") or "").strip(),
        "",
        f"#снегири #{tag} #техника #гири #гиревойспорт",
    ]
    return "\n".join(x for x in lines if x is not None)


async def build_technique_slot() -> tuple[str, str | None, str | None, dict | None]:
    entry = pick_entry()
    if not entry:
        body = f"{TOPIC_TAG}\n\nСегодня без видео-разбора — очередь техники пуста или клипы offline."
        return f"{TOPIC_TAG} fallback", body, None, None

    eid = entry["id"]
    topic = f"{TOPIC_TAG} {entry.get('headline', eid)} (id={eid})"
    body = format_post(entry)
    clip_rel = (entry.get("clip_file") or (entry.get("video") or {}).get("subtitled_file") or "").strip()
    video_path = str(_ROOT / clip_rel) if clip_rel else None
    return topic, body, video_path, {"_kind": "stern_technique", "entry_id": eid}


def record_published(entry_id: str) -> None:
    """После успешной публикации в канал."""
    if entry_id:
        mark_used(entry_id)


def entry_id_from_topic(topic_raw: str | None) -> str | None:
    import re

    m = re.search(r"\(id=([^)]+)\)", topic_raw or "")
    return m.group(1).strip() if m else None
