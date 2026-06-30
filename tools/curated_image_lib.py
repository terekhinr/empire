"""Общая логика манифеста картинок для курированного автопоста (Nano Banana)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLES_PATH = ROOT / "data" / "curated_image_styles.json"
EXPORT = ROOT / "docs" / "content_factory" / "gemini_export"
GDEPAR_MATRIX = EXPORT / "gdepar_topic_matrix.json"
STERN_MATRIX = EXPORT / "stern_topic_matrix.json"
STERN_INGESTED = EXPORT / "generated" / "stern_all_ingested.md"
MANIFEST_PATH = ROOT / "data" / "curated_topic_images_manifest.json"
CLASSIC_BANYA_PATH = ROOT / "data" / "gdepar_classic_banya.json"
CLASSIC_MEDIA_DIR = ROOT / "media" / "gdepar" / "classic"

POST_BLOCK_RE = re.compile(
    r"---\s*\n(.*?)\n---\s*\n(.*?)(?=\n---\s*\nid:|\Z)",
    re.DOTALL,
)

RUBRIC_HASHTAG = {
    "рутина": "рутина",
    "психология": "психология",
    "восстановление": "восстановление",
    "питание": "питание",
    "срывы": "срывы",
    "мотивация": "мотивация",
    "возрастной тренинг": "тренинг",
    "ответы": "ответы",
}


def load_styles() -> dict:
    return json.loads(STYLES_PATH.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def rubric_from_topic_raw(topic_raw: str) -> str:
    m = re.match(r"\[([^\]]+)\]", (topic_raw or "").strip())
    return (m.group(1) if m else "").strip().lower()


def hashtag_theme(topic_raw: str) -> str:
    return RUBRIC_HASHTAG.get(rubric_from_topic_raw(topic_raw), "рутина")


def stern_canonical_topic_id(topic_id: str, family: str) -> str:
    """STR-EV-016 → STR-EV-001 (15 базовых вечерних тем)."""
    prefix = "STR-EV" if family == "ev" else "STR-RT"
    n = int(topic_id.split("-")[-1])
    base_n = (n - 1) % 15 + 1
    return f"{prefix}-{base_n:03d}"


def topic_id_from_stern_post_id(post_id: str) -> str | None:
    m = re.match(r"stern_1900_ev_(\d+)_", post_id, re.I)
    if m:
        return f"STR-EV-{int(m.group(1)):03d}"
    m = re.match(r"stern_0930_(\w+)_(\d+)", post_id, re.I)
    if m:
        return f"STR-RT-{int(m.group(2)):03d}"
    return None


def parse_frontmatter(block: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def load_stern_ingested_prompts() -> dict[str, str]:
    """post_id → image_prompt_en из stern_all_ingested.md."""
    out: dict[str, str] = {}
    if not STERN_INGESTED.is_file():
        return out
    text = STERN_INGESTED.read_text(encoding="utf-8")
    for fm_raw, _body in POST_BLOCK_RE.findall(text):
        meta = parse_frontmatter(fm_raw)
        pid = meta.get("id")
        prompt = meta.get("image_prompt_en")
        if pid and prompt:
            out[pid] = prompt
    return out


def gdepar_scene_hint(entry: dict, styles: dict) -> str:
    dir_scenes = styles.get("gdepar_dir_scenes") or {}
    d = (entry.get("dir") or "BT").upper()
    headline = (entry.get("headline") or "").strip()
    base = dir_scenes.get(d, dir_scenes.get("BT", "wooden banya still life"))
    return f"{base}, theme suggests: {headline[:80]}"


def gdepar_prompt_en(topic_raw: str, scene_en: str, styles: dict | None = None, *, provider: str = "gemini") -> str:
    """Канонический промпт Gdepar: Gemini-веники из gdepar_content, иначе scene+style."""
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import gdepar_content as gc

    prompt_prov = "gemini" if provider in ("gemini", "fal-nb", "fal_nb") else provider
    canon = gc.resolve_gdepar_image_prompt(topic_raw, provider=prompt_prov)
    if canon:
        return canon
    return build_full_prompt("gdepar", scene_en, styles)


GDEPAR_TAG_TO_DIR = {
    "веник": "TR",
    "парение": "TR",
    "пар": "TR",
    "новичок": "NW",
    "печь": "TE",
    "камни": "TE",
    "техника": "TE",
    "вентиляция": "TE",
    "быт": "BT",
    "гигиена": "BT",
    "этикет": "BT",
    "практика": "PS",
    "детокс": "PS",
    "здоровье": "GN",
    "вода": "GN",
    "маркетинг": "GN",
    "напитки": "RC",
    "рецепты": "RC",
    "традиции": "FL",
    "байки": "FL",
    "карта": "MP",
    "отзывы": "MP",
    "поиск": "MP",
    "психология": "PS",
}


def gdepar_dir_for_post(tag: str | None, headline: str = "") -> str:
    t = (tag or "").strip().lower()
    if t in GDEPAR_TAG_TO_DIR:
        return GDEPAR_TAG_TO_DIR[t]
    low = (headline or "").lower()
    if "веник" in low or "берёз" in low or "берез" in low or "дуб" in low:
        return "TR"
    if "печ" in low or "камен" in low or "электропеч" in low:
        return "TE"
    if "нович" in low or "перв" in low:
        return "NW"
    return "BT"


def channel_image_provider(channel: str, styles: dict | None = None) -> str:
    styles = styles or load_styles()
    ch = (styles.get("channels") or {}).get(channel) or {}
    return (ch.get("image_provider") or "gemini").strip().lower()


def stern_scene_hint(topic_raw: str, fallback: str = "") -> str:
    if fallback:
        return fallback.strip()
    rub = rubric_from_topic_raw(topic_raw)
    hints = {
        "рутина": "home office morning routine prop, chair or floor exercise corner",
        "психология": "tired worker desk closed laptop, kettlebell on floor",
        "восстановление": "dark bedroom or calm living room rest mood",
        "питание": "simple kitchen table water glass black coffee",
        "срывы": "messy evening kitchen table after long workday",
        "мотивация": "paper notebook calendar marks near kettlebell",
        "возрастной тренинг": "kettlebell on gym mat careful training mood",
        "ответы": "notebook pen kettlebell pragmatic setup",
    }
    return hints.get(rub, "home office kettlebell still life")


def build_full_prompt(channel: str, scene_en: str, styles: dict | None = None) -> str:
    styles = styles or load_styles()
    ch = (styles.get("channels") or {}).get(channel) or {}
    parts = [scene_en.strip().rstrip(".")]
    if ch.get("scene_rules"):
        parts.append(ch["scene_rules"])
    if ch.get("style_suffix"):
        parts.append(ch["style_suffix"])
    if ch.get("negative"):
        parts.append(f"Avoid: {ch['negative']}")
    return ". ".join(p for p in parts if p) + "."


def output_path(channel: str, key: str, styles: dict | None = None) -> str:
    styles = styles or load_styles()
    ch = (styles.get("channels") or {}).get(channel) or {}
    media_dir = ch.get("media_dir") or f"media/{channel}/topics"
    safe = re.sub(r"[^\w\-]+", "_", key).strip("_")
    return f"{media_dir}/{safe}.jpg"


def audit_gdepar_classic_banya() -> dict:
    """Рубрика 15:00 — портреты авторов, уже в Empire. Nano Banana не нужен."""
    if not CLASSIC_BANYA_PATH.is_file():
        return {"entries": 0, "on_disk": 0, "ready": False}
    data = json.loads(CLASSIC_BANYA_PATH.read_text(encoding="utf-8"))
    entries = list(data.get("entries") or [])
    on_disk = 0
    for entry in entries:
        eid = (entry.get("id") or "").strip()
        if not eid:
            continue
        dest = CLASSIC_MEDIA_DIR / f"{eid}.jpg"
        if dest.is_file() and dest.stat().st_size > 2048:
            on_disk += 1
    return {
        "entries": len(entries),
        "on_disk": on_disk,
        "media_dir": str(CLASSIC_MEDIA_DIR.relative_to(ROOT)),
        "data_file": str(CLASSIC_BANYA_PATH.relative_to(ROOT)),
        "slot": "15:00",
        "ready": on_disk >= len(entries) * 0.9 if entries else False,
    }


def classic_banya_manifest_items() -> list[dict]:
    """Записи в манифесте со status=existing — только учёт, не генерировать."""
    if not CLASSIC_BANYA_PATH.is_file():
        return []
    data = json.loads(CLASSIC_BANYA_PATH.read_text(encoding="utf-8"))
    items: list[dict] = []
    for entry in data.get("entries") or []:
        eid = (entry.get("id") or "").strip()
        if not eid:
            continue
        out = f"media/gdepar/classic/{eid}.jpg"
        dest = ROOT / out
        items.append(
            {
                "channel": "gdepar",
                "rubrique": "classic_banya",
                "topic_id": eid,
                "topic_raw": f"[Классическая баня] {entry.get('author', '')}, {entry.get('work', '')}",
                "output_file": out,
                "bind_mode": "classic_entry",
                "image_source": "wikipedia_commons_portrait",
                "status": "existing" if dest.is_file() and dest.stat().st_size > 2048 else "missing_file",
                "skip_nanobanana": True,
            }
        )
    return items


def manifest_item(
    *,
    channel: str,
    topic_id: str,
    topic_raw: str,
    scene_en: str,
    bind_key: str,
    bind_mode: str,
    post_ids: list[str] | None = None,
    pool: str | None = None,
    styles: dict | None = None,
    image_provider: str | None = None,
) -> dict:
    styles = styles or load_styles()
    ch = (styles.get("channels") or {}).get(channel) or {}
    prov = (image_provider or channel_image_provider(channel, styles)).strip().lower()
    if channel == "gdepar":
        full = gdepar_prompt_en(topic_raw, scene_en, styles, provider=prov)
    else:
        full = build_full_prompt(channel, scene_en, styles)
    return {
        "channel": channel,
        "topic_id": topic_id,
        "topic_raw": topic_raw,
        "hashtag_theme": hashtag_theme(topic_raw),
        "scene_en": scene_en,
        "prompt_en": full,
        "image_provider": prov,
        "output_file": output_path(channel, topic_id, styles),
        "bind_key": bind_key,
        "bind_mode": bind_mode,
        "post_ids": post_ids or [],
        "pool": pool,
        "aspect_ratio": ch.get("aspect_ratio", "4:3"),
        "status": "pending",
    }
