"""Готовые рубричные посты: цитата + источник + картинка (без LLM)."""

from __future__ import annotations

import json
import logging
import random
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger("empire.rubric_posts")

_WIKI_UA = (
    "EmpireRubricBot/1.0 (+https://gdepar.ru; lenin/curated) Python-httpx"
)

# Минимум для «карточки» (legacy). Рубрики lenin/stern — разворот LLM (см. RUBRIC_EXPAND_*).
MIN_CURATED_BODY_CHARS = 260
RUBRIC_EXPAND_MIN_CHARS = 550
RUBRIC_EXPAND_MAX_CHARS = 950


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def image_candidate_urls(entry: dict) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        u = (u or "").strip()
        if u and u not in seen:
            seen.add(u)
            out.append(u)

    raw = (entry.get("image_file") or "").strip()
    if not raw and entry.get("image_url"):
        tail = str(entry["image_url"]).rsplit("/", 1)[-1]
        if tail.startswith(("440px-", "640px-", "320px-", "800px-")):
            raw = tail.split("-", 1)[-1]
        elif tail and "." in tail:
            raw = tail
    if raw:
        enc = quote(raw.replace(" ", "_"), safe="/")
        add(f"https://commons.wikimedia.org/wiki/Special:FilePath/{enc}?width=800")
    add(entry.get("image_url") or "")
    return out


async def download_image(url: str, dest: Path, *, timeout: float = 12.0) -> bool:
    import httpx

    headers = {"User-Agent": _WIKI_UA, "Accept": "image/*,*/*;q=0.8"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200 or len(r.content) < 2048:
            return False
        ctype = (r.headers.get("content-type") or "").lower()
        if "html" in ctype and "image" not in ctype:
            return False
        dest.write_bytes(r.content)
        return dest.stat().st_size >= 2048


async def ensure_entry_image(entry: dict, media_dir: Path, default_name: str = "_default.jpg") -> str | None:
    eid = (entry.get("id") or "item").strip()
    media_dir.mkdir(parents=True, exist_ok=True)
    dest = media_dir / f"{eid}.jpg"
    if dest.is_file() and dest.stat().st_size > 2048:
        return str(dest)
    for url in image_candidate_urls(entry):
        try:
            if await download_image(url, dest):
                return str(dest)
        except Exception as exc:
            logger.warning("rubric img %s: %s", eid, type(exc).__name__)
    fb = media_dir / default_name
    if fb.is_file():
        return str(fb)
    return None


def pick_entry(
    data_path: Path,
    history_path: Path,
    *,
    rubric: str | None = None,
) -> dict | None:
    data = load_json(data_path)
    rubrics = data.get("rubrics", data)
    if rubric:
        entries = rubrics.get(rubric, {}).get("entries", [])
        if not entries and isinstance(rubrics.get(rubric), list):
            entries = rubrics[rubric]
    else:
        entries = data.get("entries", [])
    if not entries:
        return None
    used: dict = {}
    if history_path.is_file():
        try:
            used = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            used = {}
    key = rubric or "_all"
    used_ids = set((used.get("by_rubric") or {}).get(key, []))
    pool = [
        e
        for e in entries
        if e.get("id") not in used_ids
        and not e.get("deprecated")
        and (entry_quote(e) or e.get("text"))
    ] or [
        e for e in entries if not e.get("deprecated") and (entry_quote(e) or e.get("text"))
    ]
    entry = random.choice(pool)
    by_rubric = used.setdefault("by_rubric", {})
    ids = list(by_rubric.get(key, []))
    ids.append(entry.get("id"))
    by_rubric[key] = ids[-40:]
    used["last"] = datetime.utcnow().isoformat()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def entry_quote(entry: dict) -> str:
    """Основной текст поста: полная цитата или разбор (не комментарий редактора)."""
    return (entry.get("quote") or entry.get("text") or "").strip()


def entry_commentary(entry: dict) -> str:
    return (entry.get("note") or entry.get("mikhalych") or "").strip()


def entry_source_line(entry: dict) -> str:
    if entry.get("author") and entry.get("work"):
        return f"{entry['author']}, {entry['work']}"
    return (entry.get("source") or "").strip()


def make_rubric_seed(
    *,
    persona: str,
    rubric_key: str,
    title: str,
    emoji: str,
    entry: dict,
    min_chars: int = RUBRIC_EXPAND_MIN_CHARS,
    max_chars: int = RUBRIC_EXPAND_MAX_CHARS,
) -> dict:
    """Якорь для LLM-разворота (вариант 2): факты только из entry."""
    return {
        "persona": persona,
        "rubric_key": rubric_key,
        "entry_id": entry.get("id"),
        "title": title,
        "emoji": emoji,
        "quote": entry_quote(entry),
        "source": entry_source_line(entry),
        "note": entry_commentary(entry),
        "period": (entry.get("period") or "").strip(),
        "min_chars": min_chars,
        "max_chars": max_chars,
    }


def rubric_expansion_prompt_block(seed: dict, *, extra_rules: str = "") -> str:
    """Блок для generate_draft_content: развернуть якорь в один TG-пост."""
    quote = (seed.get("quote") or "").strip()
    source = (seed.get("source") or "").strip()
    note = (seed.get("note") or "").strip()
    period = (seed.get("period") or "").strip()
    title = seed.get("title") or "Рубрика"
    emoji = seed.get("emoji") or "📌"
    lo = int(seed.get("min_chars") or RUBRIC_EXPAND_MIN_CHARS)
    hi = int(seed.get("max_chars") or RUBRIC_EXPAND_MAX_CHARS)
    lines = [
        f"\nРЕЖИМ «РУБРИКА · РАЗВОРОТ» ({title}):\n",
        f"Заголовок поста: {emoji} и название рубрики «{title}» — одной строкой с <b>.\n",
        f"ОБЪЁМ основного текста (без хэштегов): {lo}–{hi} знаков — один нормальный пост Telegram, не карточка.\n",
        "СТРУКТУРА:\n",
        "  • 1–2 абзаца зацепки: зачем это читателю сегодня;\n",
        "  • 1–2 абзаца контекста, опираясь ТОЛЬКО на якорь ниже;\n",
        "  • мысль якоря — своими словами, можно короткая цитата в «кавычках», не длиннее 2 строк;\n",
        "  • строка «Источник: …» — ДОСЛОВНО как в якоре;\n",
        "  • если в якоре есть комментарий канала — 1–2 предложения в конце, без морали.\n",
        "ЖЁСТКИЙ ЯКОРЬ (не добавляй фактов, имён, дат, цитат вне этого блока):\n",
        f"  • Тезис: «{quote}»\n",
    ]
    if period:
        lines.append(f"  • Период: {period}\n")
    if source:
        lines.append(f"  • Источник (скопировать в пост): {source}\n")
    if note:
        lines.append(f"  • Комментарий канала (можно сжать, смысл сохранить): {note}\n")
    lines.append(
        "ЗАПРЕТЫ: не выдумывай новые источники; не превращай пост в blockquote из одной фразы; "
        "не пиши «парадокс?», «актуально сегодня», не раздувай тему в сторону от якоря.\n"
    )
    if extra_rules:
        lines.append(extra_rules.strip() + "\n")
    return "".join(lines)


def curated_body_length(entry: dict) -> int:
    parts = [entry_quote(entry)]
    if entry.get("author") and entry.get("work"):
        parts.append(f"{entry['author']}, {entry['work']}")
    elif entry.get("source"):
        parts.append(str(entry["source"]))
    parts.append(entry_commentary(entry))
    return sum(len(p) for p in parts if p)


def format_curated_post(
    title: str,
    emoji: str,
    entry: dict,
    *,
    hashtags: str,
    source_label: str = "Источник",
    commentary_prefix: str = "💬",
    show_commentary: bool = True,
) -> str:
    """HTML-пост: заголовок, цитата в blockquote, источник, опционально комментарий канала."""
    quote = entry_quote(entry)
    if entry.get("author") and entry.get("work"):
        src = f"{entry['author']}, {entry['work']}"
    else:
        src = (entry.get("source") or "").strip()
    comment = entry_commentary(entry)
    caption = (entry.get("image_caption") or "").strip()
    lines = [f"{emoji} <b>{title}</b>", ""]
    if quote:
        lines.append(f"<blockquote>{quote}</blockquote>")
    if src:
        lines.append("")
        lines.append(f"<i>{source_label}: {src}</i>")
    if caption:
        lines.extend(["", f"<i>{caption}</i>"])
    if show_commentary and comment:
        lines.append("")
        if commentary_prefix:
            lines.append(f"{commentary_prefix} {comment}")
        else:
            lines.append(comment)
    lines.extend(["", hashtags])
    return "\n".join(lines)


def parse_entry_id_from_topic(topic_raw: str) -> str | None:
    m = re.search(r"\(id=([^)]+)\)", topic_raw or "")
    return m.group(1).strip() if m else None


def pick_sibling_entry(entries: list[dict], exclude_id: str | None) -> dict:
    pool = [e for e in entries if e.get("id") != exclude_id] or list(entries)
    return random.choice(pool)


def _rubric_key_from_topic(topic_raw: str, tag_to_key: dict[str, str]) -> str | None:
    for tag, key in tag_to_key.items():
        if tag in (topic_raw or ""):
            return key
    return None


async def curated_resample(persona_key: str, topic_raw: str) -> tuple[str, str, str | None] | None:
    """
    Другой выпуск той же curated-рубрики: новая цитата + подходящее фото.
    Возвращает (topic_raw, html_text, image_path) или None, если тема не curated.
    """
    root = Path(__file__).resolve().parent
    current_id = parse_entry_id_from_topic(topic_raw)

    if persona_key == "gdepar" and "[Классическая баня]" in (topic_raw or ""):
        import gdepar_content as gc

        data = load_json(root / "data" / "gdepar_classic_banya.json")
        entries = data.get("entries", [])
        if not entries:
            return None
        entry = pick_sibling_entry(entries, current_id)
        topic = (
            f"{gc.CLASSIC_RUBRIC_TAG} {entry.get('author', '')}, {entry.get('work', '')} "
            f"(id={entry.get('id', '')})"
        )
        text = gc.format_classic_banya_post(entry)
        img = await gc.ensure_classic_image(entry)
        return topic, text, img

    if persona_key == "lenin":
        import lenin_content as lc

        tag_to_key = {v: k for k, v in lc.RUBRIC_TOPIC_TAGS.items()}
        rubric = _rubric_key_from_topic(topic_raw, tag_to_key)
        if not rubric:
            return None
        data = load_json(root / "data" / "lenin_rubrics.json")
        entries = (data.get("rubrics") or {}).get(rubric, {}).get("entries", [])
        if not entries:
            return None
        entry = pick_sibling_entry(entries, current_id)
        meta = (data.get("rubrics") or {}).get(rubric, {})
        topic = f"{lc.RUBRIC_TOPIC_TAGS[rubric]} {entry.get('source', '')} (id={entry.get('id', '')})"
        img = await ensure_entry_image(entry, root / "media" / "lenin" / "rubrics", "_default_lenin.jpg")
        seed = make_rubric_seed(
            persona="lenin",
            rubric_key=rubric,
            title=meta.get("title", rubric),
            emoji=meta.get("emoji", "📌"),
            entry=entry,
        )
        from main import generate_draft_content

        text, _img_p = await generate_draft_content("lenin", topic, rubric_seed=seed)
        return topic, text, img

    if persona_key == "stern":
        import stern_content as sc

        tag_to_key = {v: k for k, v in sc.RUBRIC_TOPIC_TAGS.items()}
        rubric = _rubric_key_from_topic(topic_raw, tag_to_key)
        if not rubric:
            return None
        if rubric == "athletic_legacy":
            data = load_json(root / "data" / "stern_athletic_legacy.json")
        else:
            data = load_json(root / "data" / "stern_rubrics.json")
        entries = (data.get("rubrics") or {}).get(rubric, {}).get("entries", [])
        if not entries:
            return None
        entry = pick_sibling_entry(entries, current_id)
        meta = (data.get("rubrics") or {}).get(rubric, {})
        label = entry.get("headline") or entry.get("name") or entry.get("source", "")
        topic = f"{sc.RUBRIC_TOPIC_TAGS[rubric]} {label} (id={entry.get('id', '')})"
        img = await ensure_entry_image(entry, root / "media" / "stern" / "rubrics", "_default_stern.jpg")
        if rubric == "athletic_legacy":
            import stern_athletic_legacy as sal

            if sal.is_ready_entry(entry):
                return topic, sal.format_athletic_legacy_post(entry), img
            seed = sal.make_athletic_legacy_seed(entry)
        else:
            seed = make_rubric_seed(
                persona="stern",
                rubric_key=rubric,
                title=meta.get("title", rubric),
                emoji=meta.get("emoji", "🏋️"),
                entry=entry,
            )
        from main import generate_draft_content

        text, _img_p = await generate_draft_content("stern", topic, rubric_seed=seed)
        return topic, text, img

    return None
