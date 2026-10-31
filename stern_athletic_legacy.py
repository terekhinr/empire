"""Рубрика «Историческое наследие и выдающиеся атлеты» — Снегири/Штерн."""

from __future__ import annotations

import re
from pathlib import Path

import rubric_posts

_ROOT = Path(__file__).resolve().parent
_DATA_PATH = _ROOT / "data" / "stern_athletic_legacy.json"
_HISTORY_PATH = _ROOT / "data" / "stern_athletic_legacy_used.json"
_MEDIA_DIR = _ROOT / "media" / "stern" / "rubrics"

RUBRIC_KEY = "athletic_legacy"
TOPIC_TAG = "[Историческое наследие]"
TITLE = "Историческое наследие и выдающиеся атлеты"
EMOJI = "🏛️"

EXPAND_MIN = 1100
EXPAND_MAX = 1900


def load_data() -> dict:
    return rubric_posts.load_json(_DATA_PATH)


def is_ready_entry(entry: dict) -> bool:
    if entry.get("deprecated"):
        return False
    if entry.get("verbatim") or entry.get("status") == "ready":
        return bool(entry.get("body_html") or entry.get("quote") or entry.get("text"))
    return False


def _facts_html(entry: dict) -> str:
    facts = entry.get("facts") or []
    if isinstance(facts, str):
        return facts.strip()
    if not facts:
        return ""
    return "\n".join(f"• {str(f).strip()}" for f in facts if str(f).strip())


def _limit_trailing_hashtags(text: str, max_n: int = 3) -> str:
    """В конце поста оставляем не больше max_n хэштегов (лимит TG-аудита)."""
    lines = (text or "").rstrip().split("\n")
    if not lines:
        return text or ""
    last = lines[-1].strip()
    tags = [t for t in last.split() if t.startswith("#")]
    if not tags:
        return text or ""
    rest = [t for t in last.split() if not t.startswith("#")]
    lines[-1] = (" ".join(rest + tags[:max_n])).strip()
    return "\n".join(lines).rstrip()


def format_athletic_legacy_post(entry: dict) -> str:
    """HTML для готового выпуска (verbatim / status=ready)."""
    if entry.get("body_html"):
        body = entry["body_html"].strip()
        if not body.startswith(EMOJI):
            tag = entry.get("tag", "наследие")
            if "#" not in body:
                body += f"\n\n#снегири #{tag} #история"
        return _limit_trailing_hashtags(body, 3)

    headline = (entry.get("headline") or entry.get("name") or "Атлет").strip()
    tag = entry.get("tag", "наследие")
    lines = [f"{EMOJI} <b>{headline}</b>", ""]

    bio = (entry.get("bio") or "").strip()
    if bio:
        lines.extend([f"<b>Короткая биография:</b>", bio, ""])

    facts = _facts_html(entry)
    if facts:
        lines.extend([f"<b>Интересные факты из жизни:</b>", facts, ""])

    legacy = (entry.get("legacy") or entry.get("note") or "").strip()
    if legacy:
        lines.extend([f"<b>Наследие:</b>", legacy, ""])

    if entry.get("kind") == "technique":
        cues = entry.get("key_cues") or []
        if isinstance(cues, str):
            cues = [cues]
        if cues:
            lines.extend([f"<b>Ключевые акценты:</b>", "\n".join(f"• {c}" for c in cues if str(c).strip()), ""])
        commentary = (entry.get("commentary") or entry.get("video_commentary") or "").strip()
        if commentary:
            lines.extend([f"<b>Разбор видео:</b>", commentary, ""])
        clip = (entry.get("clip_file") or entry.get("video_clip") or "").strip()
        if clip:
            lines.append(f"🎬 <i>Клип: {clip}</i>")
            lines.append("")

    src = rubric_posts.entry_source_line(entry) or (entry.get("source") or "").strip()
    if src:
        lines.extend([f"<i>Источник: {src}</i>", ""])

    # ≤3 хэштега (аудит stern)
    lines.append(f"#снегири #{tag} #история")
    return "\n".join(lines)


def make_athletic_legacy_seed(entry: dict) -> dict:
    kind = entry.get("kind") or "biography"
    return {
        "persona": "stern",
        "rubric_key": RUBRIC_KEY,
        "entry_id": entry.get("id"),
        "title": TITLE,
        "emoji": EMOJI,
        "kind": kind,
        "name": entry.get("name") or entry.get("headline", ""),
        "headline": entry.get("headline") or entry.get("name", ""),
        "block": entry.get("block"),
        "block_title": entry.get("block_title", ""),
        "era": entry.get("era") or entry.get("period", ""),
        "seed_text": (entry.get("seed") or entry.get("text") or entry_quote(entry)).strip(),
        "source": rubric_posts.entry_source_line(entry) or (entry.get("source") or ""),
        "min_chars": int(entry.get("min_chars") or EXPAND_MIN),
        "max_chars": int(entry.get("max_chars") or EXPAND_MAX),
    }


def entry_quote(entry: dict) -> str:
    return (entry.get("quote") or entry.get("text") or entry.get("seed") or "").strip()


def expansion_prompt_block(seed: dict, *, extra_rules: str = "") -> str:
    kind = seed.get("kind") or "biography"
    lo = int(seed.get("min_chars") or EXPAND_MIN)
    hi = int(seed.get("max_chars") or EXPAND_MAX)
    name = seed.get("name") or seed.get("headline") or "атлет"
    era = (seed.get("era") or "").strip()
    anchor = (seed.get("seed_text") or "").strip()
    source = (seed.get("source") or "биографические справочники, обобщение").strip()

    if kind == "technique":
        return (
            f"\nРЕЖИМ «ИСТОРИЧЕСКОЕ НАСЛЕДИЕ · ТЕХНИКА» ({name}):\n"
            f"Заголовок: {EMOJI} <b>{name}</b> — одной строкой.\n"
            f"ОБЪЁМ: {lo}–{hi} знаков без хэштегов.\n"
            "СТРУКТУРА (жирные подзаголовки через <b>):\n"
            "  <b>Суть движения</b> — 1–2 абзаца, биомеханика простым языком;\n"
            "  <b>Ключевые акценты</b> — 3–5 буллетов «• » (setup, фазы, дыхание);\n"
            "  <b>Типичные ошибки</b> — 2–3 пункта;\n"
            "  <b>Связь с наследием</b> — 1 абзац: как это делали атлеты из рубрики или зачем здоровью спины;\n"
            f"  строка <i>Источник: {source}</i>.\n"
            f"ЯКОРЬ (техника только отсюда; цифры весов — только если в якоре):\n  {anchor}\n"
            "ЗАПРЕТЫ: соревновательные разряды/WKSF, выдуманные рекорды, пошаговый «медицинский» диагноз.\n"
            + (extra_rules.strip() + "\n" if extra_rules else "")
        )

    if kind == "trick":
        return (
            f"\nРЕЖИМ «ИСТОРИЧЕСКОЕ НАСЛЕДИЕ · ТРЮК/СНАРЯД» ({name}):\n"
            f"Заголовок: {EMOJI} <b>{name}</b> — одной строкой.\n"
            f"ОБЪЁМ: {lo}–{hi} знаков без хэштегов.\n"
            "СТРУКТУРА (жирные подзаголовки через <b>):\n"
            "  <b>Суть трюка или снаряда</b> — 1–2 абзаца;\n"
            "  <b>Кто выполнял</b> — 2–4 имени/эпохи из якоря;\n"
            "  <b>Как повторить или почему опасно</b> — практично, без пошаговой «инструкции риска»;\n"
            f"  строка <i>Источник: {source}</i>.\n"
            f"ЯКОРЬ (не выходи за рамки, не выдумывай рекорды и даты):\n  {anchor}\n"
            "ЗАПРЕТЫ: соревновательный гиревой спорт (разряды, WKSF), выдуманные цифры, "
            "«актуально сегодня», blockquote из одной фразы.\n"
            + (extra_rules.strip() + "\n" if extra_rules else "")
        )

    return (
        f"\nРЕЖИМ «ИСТОРИЧЕСКОЕ НАСЛЕДИЕ · АТЛЕТ» ({name}):\n"
        f"Заголовок: {EMOJI} <b>{name}</b> — с коротким подзаголовком через двоеточие.\n"
        f"ОБЪЁМ: {lo}–{hi} знаков без хэштегов.\n"
        "СТРУКТУРА (жирные подзаголовки через <b>, между блоками пустая строка):\n"
        "  <b>Короткая биография:</b> 2–4 предложения;\n"
        "  <b>Интересные факты из жизни:</b> 3 буллета через «• »;\n"
        "  <b>Наследие:</b> 2–3 предложения — урок для современного зала/здоровья спины;\n"
        f"  строка <i>Источник: {source}</i>.\n"
        + (f"Эпоха: {era}.\n" if era else "")
        + f"ЯКОРЬ (факты только отсюда; если мало — общие формулировки без конкретных цифр):\n  {anchor}\n"
        "ЗАПРЕТЫ: выдуманные рекорды, тома, страницы; соревновательный гиревой спорт; "
        "«парадокс?», «актуально сегодня».\n"
        + (extra_rules.strip() + "\n" if extra_rules else "")
    )


async def build_athletic_legacy_slot(
    *, weekday: int = 0
) -> tuple[str, str | None, str | None, dict | None]:
    data = load_data()
    entry = rubric_posts.pick_entry(
        _DATA_PATH, _HISTORY_PATH, rubric=RUBRIC_KEY, global_cooldown_days=30
    )
    if not entry:
        body = f"{TOPIC_TAG}\n\nСегодня без выпуска — завтра снова разбор наследия."
        return f"{TOPIC_TAG} fallback", body, None, None

    label = entry.get("headline") or entry.get("name") or entry.get("id", "")
    topic = f"{TOPIC_TAG} {label} (id={entry.get('id', '')})"
    img = await rubric_posts.ensure_entry_image(entry, _MEDIA_DIR, "_default_stern.jpg")

    if is_ready_entry(entry):
        return topic, format_athletic_legacy_post(entry), img, None

    return topic, None, img, make_athletic_legacy_seed(entry)


def parse_entry_id_from_topic(topic_raw: str) -> str | None:
    m = re.search(r"\(id=([^)]+)\)", topic_raw or "")
    return m.group(1).strip() if m else None
