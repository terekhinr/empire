"""Спец-посты канала Ленин: донат, рубрики «в литературе / искусстве / биографии / кино»."""

from __future__ import annotations

import json
import random
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from donate_links import donate_deep_link

import rubric_posts

_ROOT = Path(__file__).resolve().parent
_SUPPORT_PATH = _ROOT / "data" / "lenin_support_copy.json"
_BEDTIME_PATH = _ROOT / "data" / "lenin_bedtime_stories.json"
_BEDTIME_HISTORY = _ROOT / "data" / "lenin_bedtime_used.json"
_RUBRICS_PATH = _ROOT / "data" / "lenin_rubrics.json"
_REV_CALENDAR_PATH = _ROOT / "data" / "lenin" / "revolutionary_calendar.txt"
_RUBRICS_HISTORY = _ROOT / "data" / "lenin_rubrics_used.json"
_RUBRICS_MEDIA = _ROOT / "media" / "lenin" / "rubrics"
_PSS_TOPICS_PATH = _ROOT / "data" / "lenin_pss_topics.json"
_PSS_USED_PATH = _ROOT / "data" / "lenin_pss_used.json"

RUBRIC_ROTATION = ("literature", "art", "biography", "cinema")

RUBRIC_TOPIC_TAGS = {
    "literature": "[Ленин в литературе]",
    "art": "[Ленин в искусстве]",
    "biography": "[Ленин · биография]",
    "cinema": "[Ленин в кино]",
}

# Повторяющийся LLM-сюжет «Невская Звезда / полемика в газетах» — не публиковать снова.
LENIN_PRESS_STORY_MARKERS = (
    "невск",
    "полемик",
    "печатный орган",
    "теряют читател",
    "актуальн",
    "обсужден",
    "сухим и неинтересн",
    "нужно больше",
)

# Клише в LLM-слотах (19:00 цитата/анализ) — не повторять из поста в пост.
LENIN_CLICHE_PHRASES = (
    "сим победиши",
    "сим — победиши",
    "ленин vs бюрократ",
    "парадокс? нет",
    "парадокс? нет.",
    "звучит особенно актуально",
    "революция победила не только",
    "беспощадная борьба с разгильдяйством",
    "канцелярский метод",
    "канцелярск",
    "бюрократ",
    "газет",
    "редакци",
    "типограф",
    "чиновник",
    "аппарат управлен",
    "🔥 ленин",
    "выходишь обновлённым",
    "детектив решений",
    "святой миф",
)

# Темы ПСС, которые LLM часто дублирует в календаре/марксизме — реже подряд.
PSS_TOPIC_COOLDOWN_IDS = frozenset({"pss_state_apparatus", "pss_press_censorship"})

# Вечерний RAG-тема «Печать» часто тянет тот же фрагмент про полемику — отключена.
PSS_TOPIC_DISABLED_IDS = frozenset({"pss_press_censorship"})

_MSK = ZoneInfo("Europe/Moscow")
_MONTHS_RU_GEN = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)


def calculate_old_style(day: int, month: int, year: int) -> str:
    try:
        dt = datetime(year, month, day)
        offset = 13 if year >= 1900 else 12
        old_dt = dt - timedelta(days=offset)
        return f"{old_dt.day} {_MONTHS_RU_GEN[old_dt.month - 1]}"
    except Exception:
        return "—"


def revolutionary_calendar_line(when: datetime | None = None) -> str | None:
    """Строка из data/lenin/revolutionary_calendar.txt на дату."""
    when = when or datetime.now(_MSK)
    prefix = f"{when.day:02d}.{when.month:02d}."
    if not _REV_CALENDAR_PATH.is_file():
        return None
    for line in _REV_CALENDAR_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith(prefix) and ("—" in s or "-" in s):
            return s
    return None


def make_calendar_seed(when: datetime | None = None) -> dict | None:
    """Данные для LLM-поста «Революционный календарь» (развёрнутый формат)."""
    when = when or datetime.now(_MSK)
    line = revolutionary_calendar_line(when)
    if not line:
        return None
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})\s*[—\-]\s*(.*)", line)
    if not m:
        return None
    d, mo, y, event = m.groups()
    di, mi, yi = int(d), int(mo), int(y)
    old_date = calculate_old_style(di, mi, yi)
    event_clean = event.strip().rstrip(".")
    month_name = _MONTHS_RU_GEN[mi - 1]
    headline = f"Революционный календарь: {di} {month_name} {yi} года"
    opening = (
        f"В этот день (по старому календарю {old_date}) {yi} года {event_clean}."
    )
    return {
        "_kind": "lenin_calendar",
        "topic": f"[#Вэтотдень] {headline}",
        "headline": headline,
        "event_line": line,
        "event_desc": event_clean,
        "day": di,
        "month": mi,
        "year": yi,
        "old_date": old_date,
        "opening": opening,
        "min_chars": 1100,
        "rag_query": f"{event_clean} Ленин {yi} год ПСС политбюро",
    }


def calendar_prompt_block(seed: dict) -> str:
    """Жёсткий шаблон поста как в канале: контекст, цитата ПСС, вывод."""
    headline = seed.get("headline") or ""
    opening = seed.get("opening") or ""
    return (
        "\nРЕЖИМ «РЕВОЛЮЦИОННЫЙ КАЛЕНДАРЬ» — обязательная утренняя рубрика.\n"
        f"ФАКТ ИЗ КАЛЕНДАРЯ: {seed.get('event_line', '')}\n"
        "СТРУКТУРА ПОСТА (соблюдай порядок и подзаголовки):\n"
        f"1) Первая строка текста: «{headline}»\n"
        "2) Пустая строка\n"
        f"3) ОБЯЗАТЕЛЬНОЕ начало (впиши событие с глаголом, смысл сохрани):\n"
        f"   «{opening}»\n"
        "4) Абзац: символический/исторический смысл события для эпохи (2–3 предложения, без пафоса)\n"
        "5) Строка «Исторический контекст:» и 3–4 пункта списка через «- » (факты: кто, когда, обстоятельства)\n"
        "6) Цитата Ленина в <blockquote>…</blockquote> с источником (В.И. Ленин, ПСС, т. N, стр. M) — "
        "только из БАЗЫ ЗНАНИЙ, по теме события\n"
        "7) Абзац анализа: связь с политикой, партией, властью того периода\n"
        "8) Строка «Вывод:» и итог в 2–3 предложениях\n"
        "ОБЪЁМ: 1100–1800 знаков основного текста (без хэштегов).\n"
        "ЗАПРЕТ: не начинай с эмодзи; не пиши «актуально сегодня», «парадокс? нет», «Сим победиши».\n"
        "Первый хэштег в финальной строке: #Вэтотдень\n"
    )


def build_revolutionary_calendar_post(when: datetime | None = None) -> tuple[str, str]:
    """Готовый пост календаря — факт из файла, без LLM."""
    when = when or datetime.now(_MSK)
    line = revolutionary_calendar_line(when)
    if not line:
        topic = "[#Вэтотдень] Революционный календарь"
        body = (
            "📅 <b>Революционный календарь</b>\n\n"
            f"На {when.day} {_MONTHS_RU_GEN[when.month - 1]} в файле календаря нет строки — "
            "проверьте <code>data/lenin/revolutionary_calendar.txt</code>.\n\n"
            "#ленин #история #календарь #революция"
        )
        return topic, body

    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})\s*[—\-]\s*(.*)", line)
    if not m:
        return (
            "[#Вэтотдень] Революционный календарь",
            f"📅 <b>Революционный календарь</b>\n\n{line}\n\n#ленин #история #календарь",
        )

    d, mo, y, event = m.groups()
    di, mi, yi = int(d), int(mo), int(y)
    old_date = calculate_old_style(di, mi, yi)
    event_clean = event.strip().rstrip(".")
    month_name = _MONTHS_RU_GEN[mi - 1]
    headline = f"Революционный календарь: {di} {month_name} {yi} года"
    topic = f"[#Вэтотдень] {headline}"
    opening = (
        f"В этот день (по старому календарю {old_date}) {yi} года {event_clean}."
    )
    body = (
        f"📅 <b>{headline}</b>\n\n"
        f"{opening}\n\n"
        f"<i>Источник: календарь «Ленин, соратники и эпоха СССР»</i>\n\n"
        f"#Вэтотдень #ленин #история #календарь"
    )
    return topic, body


def is_calendar_topic(topic_raw: str) -> bool:
    low = (topic_raw or "").lower()
    return "вэтотдень" in low or "революционный календарь" in low or (
        "в этот день" in low and "календар" in low
    )


def is_press_polemic_story(text: str) -> bool:
    low = (text or "").lower()
    if "невск" in low and "звезд" in low:
        return True
    if "полемик" in low and any(x in low for x in ("газет", "печат", "редакци", "издан")):
        return True
    hits = sum(1 for m in LENIN_PRESS_STORY_MARKERS if m in low)
    return hits >= 3


def recent_had_press_story(recent_bodies: list[str] | None) -> bool:
    return any(is_press_polemic_story(b) for b in (recent_bodies or []))


def filter_lenin_kb_docs(docs: list, recent_bodies: list[str] | None) -> list:
    """Убираем из RAG куски про прессу/полемику, если этот сюжет уже был недавно."""
    if not recent_had_press_story(recent_bodies):
        return docs
    banned = ("полемик", "невск", "печатн", "редакци", "цензур", "газет")
    filtered = [
        d
        for d in docs
        if not any(b in (d.page_content or "").lower() for b in banned)
    ]
    return filtered if filtered else docs


def cliche_findings(text: str, topic_raw: str = "") -> list[str]:
    findings: list[str] = []
    low = f"{text or ''} {topic_raw or ''}".lower()
    for ph in LENIN_CLICHE_PHRASES:
        if ph in low:
            findings.append(f"клише канала (уже было недавно): «{ph}»")
    if is_press_polemic_story(text):
        findings.append(
            "повтор сюжета про газеты/полемику/«Невскую Звезду» — другой документ и другой вывод"
        )
    return findings


def bodies_memory_hint(recent_bodies: list[str]) -> str:
    """Короткая память для LLM: не повторять недавние сюжеты."""
    if not recent_bodies:
        return ""
    snippets: list[str] = []
    for body in recent_bodies[:5]:
        flat = re.sub(r"<[^>]+>", " ", body)
        flat = re.sub(r"\s+", " ", flat).strip()
        if len(flat) > 120:
            flat = flat[:117] + "…"
        if flat:
            snippets.append(flat)
    if not snippets:
        return ""
    joined = "\n".join(f"  • {s}" for s in snippets)
    return (
        "\nПАМЯТЬ КАНАЛА (не повторяй эти сюжеты и формулировки близко к тексту):\n"
        f"{joined}\n"
        "Новый пост — другой документ ПСС, другой год, другой вопрос. "
        "Без вступления «парадокс?», без «актуально сегодня», без заголовков «Ленин vs …».\n"
    )


def is_special_slot(slot_value) -> str | None:
    if isinstance(slot_value, dict):
        t = slot_value.get("type") or slot_value.get("special")
        if t:
            return str(t)
    return None


def rubric_key_for_weekday(weekday: int, explicit: str | None = None) -> str:
    if explicit and explicit in RUBRIC_TOPIC_TAGS:
        return explicit
    return RUBRIC_ROTATION[weekday % len(RUBRIC_ROTATION)]


def is_curated_topic(topic_raw: str) -> bool:
    return any(tag in (topic_raw or "") for tag in RUBRIC_TOPIC_TAGS.values())


def is_verbatim_book_entry(entry: dict) -> bool:
    """Данилкин / Логинов — только цитата из книги + источник, без пересказа."""
    if entry.get("verbatim"):
        return True
    src = (entry.get("source") or "").lower()
    return "данилкин" in src or "логинов" in src


def format_rubric_post(rubric_key: str, entry: dict) -> str:
    data = rubric_posts.load_json(_RUBRICS_PATH)
    meta = (data.get("rubrics") or {}).get(rubric_key, {})
    title = meta.get("title", rubric_key)
    emoji = meta.get("emoji", "📌")
    tag = entry.get("tag", "ленин")
    show_commentary = bool(entry.get("commentary")) and is_verbatim_book_entry(entry)
    post_entry = dict(entry)
    if is_verbatim_book_entry(entry):
        post_entry["note"] = entry.get("commentary") or ""
    return rubric_posts.format_curated_post(
        title,
        emoji,
        post_entry,
        hashtags=f"#ленин #{tag} #история #мысль",
        source_label="Источник",
        commentary_prefix="💬",
        show_commentary=show_commentary,
    )


def _repair_bedtime_spacing(text: str) -> str:
    t = (text or "").replace("\u00ad", "")
    t = re.sub(r"([а-яё])([А-ЯЁ])", r"\1 \2", t)
    t = re.sub(r"([.!?»])([А-ЯЁ])", r"\1 \2", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def build_bedtime_story_post() -> tuple[str, str]:
    """Сказка на ночь: цитата из ленинианы без LLM."""
    data = rubric_posts.load_json(_BEDTIME_PATH)
    entries = data.get("entries", [])
    if not entries:
        body = (
            "🌙 <b>Сказка на ночь</b>\n\n"
            "Сегодня без выпуска — завтра снова отрывок из ленинианы.\n\n"
            "#ленин #сказка #лениниана #история"
        )
        return "[Сказка на ночь] fallback", body
    entry = rubric_posts.pick_entry(_BEDTIME_PATH, _BEDTIME_HISTORY, rubric=None)
    quote = _repair_bedtime_spacing(rubric_posts.entry_quote(entry))
    src = rubric_posts.entry_source_line(entry)
    if entry.get("author") and entry.get("work"):
        src = f"{entry['author']}, {entry['work']}"
    topic = f"[Сказка на ночь] {src} (id={entry.get('id', '')})"
    lines = ["🌙 <b>Сказка на ночь</b>", ""]
    if quote:
        lines.append(f"<blockquote>{quote}</blockquote>")
    if src:
        lines.append("")
        lines.append(f"<i>Источник: {src}</i>")
    tag = entry.get("tag", "сказка")
    lines.extend(["", f"#ленин #{tag} #лениниана #история #мысль"])
    return topic, "\n".join(lines)


def rubric_expansion_rules() -> str:
    return (
        "Канал Ленин: без «Ленин vs …», без «Сим победиши», без сюжета «газета/бюрократия/канцелярия», "
        "если этого нет в якоре. Не придумывай цитаты Ленина с томом/страницей — только источник из якоря.\n"
    )


_GENERIC_LENIN_FILES = {
    "Vladimir Lenin, 1917.jpg",
    "Vladimir Lenin after finishing his exile in Siberia, 1900-1.jpg",
    "Vladimir Lenin after finishing his exile in Siberia, 1900.jpg",
    "Lenin-poster.jpg",
    "Vladimir_Lenin.jpg",
    "Vladimir Lenin giving a speech.jpg",
}


def _visual_query_for_rubric(key: str, entry: dict) -> str | None:
    """Запрос для картины/фильма/памятника — не «Ленин портрет»."""
    custom = (entry.get("wiki_query") or entry.get("visual_query") or "").strip()
    if custom:
        return custom
    src = (entry.get("source") or "").strip()
    quote = (entry.get("quote") or entry.get("text") or "").strip()
    head = src.split("—")[0].split("–")[0].strip() if src else ""
    if key == "cinema":
        base = head or src or quote[:80]
        return f"{base} фильм" if base else None
    if key == "art":
        return head or src or None
    return None


def _is_generic_lenin_image_path(path: str | None, entry: dict | None = None) -> bool:
    if entry and (entry.get("image_file") or "") in _GENERIC_LENIN_FILES:
        return True
    if not path:
        return True
    name = Path(path).name.lower()
    if name in {"_default_lenin.jpg", "vladimir_lenin.jpg"}:
        return True
    if "1917" in name and "lenin" in name:
        return True
    return False


async def build_rubric_slot(
    rubric_key: str | None = None, *, weekday: int = 0
) -> tuple[str, str | None, str | None, dict | None]:
    """(topic, prebuilt|None, image, rubric_seed). Рубрика 12:00 — готовый HTML из JSON, без LLM."""
    key = rubric_key_for_weekday(weekday, rubric_key)
    data = rubric_posts.load_json(_RUBRICS_PATH)
    meta = (data.get("rubrics") or {}).get(key, {})
    entry = rubric_posts.pick_entry(
        _RUBRICS_PATH,
        _RUBRICS_HISTORY,
        rubric=key,
        global_cooldown_days=21,
    )
    tag = RUBRIC_TOPIC_TAGS.get(key, "[Ленин · рубрика]")
    if not entry:
        body = f"{tag}\n\nСегодня без выпуска — завтра снова выпуск рубрики."
        return f"{tag} fallback", body, None, None
    topic = f"{tag} {entry.get('source', '')} (id={entry.get('id', '')})"
    allow_default = key not in ("art", "cinema")
    default_name = "_default_lenin.jpg" if allow_default else "_no_default.jpg"
    img = await rubric_posts.ensure_entry_image(entry, _RUBRICS_MEDIA, default_name)
    visual_q = _visual_query_for_rubric(key, entry)
    seed = {
        "_kind": "lenin_rubric",
        "rubric_key": key,
        "entry_id": entry.get("id"),
        "visual_query": visual_q,
    }
    # Искусство / кино: не оставляем типичный портрет 1917 — ищем картину/кадр.
    if key in ("art", "cinema") and (
        not img or _is_generic_lenin_image_path(img, entry)
    ):
        if visual_q:
            dest = _RUBRICS_MEDIA / f"{entry.get('id') or 'item'}.jpg"
            better = await rubric_posts.fetch_wiki_page_image(visual_q, dest)
            if better:
                img = better
        if img and _is_generic_lenin_image_path(img, entry):
            img = None
    body = format_rubric_post(key, entry)
    return topic, body, img, seed


async def build_rubric_post(rubric_key: str | None = None, *, weekday: int = 0) -> tuple[str, str, str | None]:
    """Legacy: готовый HTML без LLM (тесты, откат)."""
    topic, prebuilt, img, _seed = await build_rubric_slot(rubric_key, weekday=weekday)
    if prebuilt:
        return topic, prebuilt, img
    key = rubric_key_for_weekday(weekday, rubric_key)
    entry = rubric_posts.pick_entry(
        _RUBRICS_PATH,
        _RUBRICS_HISTORY,
        rubric=key,
        global_cooldown_days=21,
    )
    if not entry:
        return topic, f"{topic}\n\nСегодня без выпуска.", img
    return topic, format_rubric_post(key, entry), img


def build_channel_support_post() -> tuple[str, str]:
    data = {}
    if _SUPPORT_PATH.is_file():
        data = json.loads(_SUPPORT_PATH.read_text(encoding="utf-8"))
    variants = data.get("variants", [])
    tags = data.get("hashtags", "#Канал #Поддержка")
    if not variants:
        body = "Поддержка канала — на хостинг и работу редактора. Ссылка на донат — в закрепе."
        return "[SPECIAL:channel_support]", body + "\n\n" + tags
    v = variants[0]
    body = f"{v['headline']}\n\n{v['body']}"
    link = donate_deep_link("lenin", "weekly_post")
    if link:
        body += f"\n\n👉 Поддержать канал: {link}"
    else:
        body += "\n\n👉 Ссылка на донат появится в закрепе (бот подключается)."
    body += f"\n\n{tags}"
    return "[SPECIAL:channel_support]", body


def _repair_pss_ocr(text: str) -> str:
    """Склейка переносов и мусора OCR из PDF ПСС."""
    if not text:
        return text
    t = text.replace("\u00ad", "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    t = re.sub(r"(\w+)¬\s*(\w+)", r"\1\2", t)
    t = t.replace("¬", "")
    t = re.sub(r"-\s*\n\s*", "", t)
    t = re.sub(r"(\w)-\s+(?=\w)", r"\1", t)
    t = re.sub(r"\s+([,.;:!?»])", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


_PSS_APPARATUS_RE = re.compile(
    r"(ЗАМЕЧАНИЯ\s+НА|ПРОЕКТ\s+ПРОГРАММЫ|ТЕКСТ\s+ПЛЕХАНОВА|ЗАМЕЧАНИЯ\s+ЛЕНИНА|"
    r"Страница\s+\d+|ПЕЧАТАЕТСЯ\s+ПО|СОЧИНЕНИЯ\s+\d+|"
    r"^\d{1,2}\.\d{2}\.\d{4}\s*—)",
    re.I | re.M,
)
_PSS_REGISTRY_RE = re.compile(r"№\s*\d+", re.I)
_PSS_LATIN_GARBAGE_RE = re.compile(r"\b[A-Za-z]{2,}\b")
_PSS_BAD_ABBR_RE = re.compile(r"\bt\.\s+(?!е\.|д\.|п\.|к\.|ч\.|г\.|н\.|с\.|т\.|э\.)[а-яё]", re.I)


def _fix_pss_ocr_glyphs(text: str) -> str:
    """Типичные подмены символов в сканах ПСС."""
    t = text
    t = re.sub(r"\bJVe\b", "№", t, flags=re.I)
    t = re.sub(r"\bIVe\b", "№", t, flags=re.I)
    t = re.sub(r"\bNo\s*(\d+)\b", r"№ \1", t, flags=re.I)
    t = re.sub(r"\bt\.\s+(?!е\.\s)([а-яё])", r"т. е. \1", t, flags=re.I)
    return t


def _yandex_speller_errors(text: str, *, max_len: int = 900) -> list[str]:
    """Орфография через API Яндекс.Спеллер (без ключей)."""
    sample = text[:max_len]
    if len(sample) < 20:
        return []
    try:
        qs = urllib.parse.urlencode({"text": sample, "lang": "ru", "options": 6})
        url = f"https://speller.yandex.net/services/spellservice/checkText?{qs}"
        with urllib.request.urlopen(url, timeout=8) as resp:
            root = ET.fromstring(resp.read())
    except (urllib.error.URLError, ET.ParseError, TimeoutError):
        return []
    out: list[str] = []
    for err in root.findall("error"):
        w = (err.findtext("word") or "").strip()
        if w:
            out.append(w)
    return out


def _pss_spell_issues(text: str) -> list[str]:
    """Сбор проблем: латиница в русском тексте, спеллер, типичный OCR."""
    issues: list[str] = []
    if _PSS_APPARATUS_RE.search(text):
        issues.append("apparatus")
    if len(_PSS_REGISTRY_RE.findall(text[:420])) >= 2:
        issues.append("registry_list")
    for m in _PSS_LATIN_GARBAGE_RE.findall(text):
        if m.lower() in {"pdf", "snk", "goelro", "nep", "comintern"}:
            continue
        issues.append(f"latin:{m}")
        break
    if _PSS_BAD_ABBR_RE.search(text):
        issues.append("bad_abbr")
    if re.search(r"^\d+\s+[А-ЯЁ]{4,}", text):
        issues.append("numbered_caps_header")
    sp = _yandex_speller_errors(text)
    # обрезок с края чанка: спеллер часто ловит «оветской» и т.п.
    for w in sp:
        if len(w) >= 5 and re.match(r"^[а-яё]", w, re.I):
            issues.append(f"spell:{w}")
            break
    return issues


def _is_pss_publishable(text: str) -> bool:
    if not text or len(text) < 120:
        return False
    if not _sentence_starts_clean(text) or not _sentence_ends_clean(text):
        return False
    if _PSS_REGISTRY_RE.search(text) or re.search(r"№\s*\d+\s*—", text):
        return False
    issues = _pss_spell_issues(text)
    if issues:
        return False
    cyr = len(re.findall(r"[а-яёА-ЯЁ]", text))
    if cyr < len(text) * 0.55:
        return False
    caps_run = re.findall(r"[А-ЯЁ]{8,}", text[:280])
    if len(caps_run) >= 2:
        return False
    return True


def _sentence_starts_clean(s: str) -> bool:
    s = s.lstrip("«\"'(\u2014\u2013- \t")
    if len(s) < 8:
        return False
    if _PSS_APPARATUS_RE.search(s[:120]):
        return False
    if re.match(r"^\d{1,2}\s+[А-ЯЁ]", s):
        return False
    if s[0].isdigit():
        return False
    if s[0].isupper() or s.startswith("«"):
        return True
    return False


def _sentence_ends_clean(s: str) -> bool:
    s = s.rstrip()
    if not s:
        return False
    if re.search(r"[.!?…»]$", s):
        return True
    return False


def _extract_complete_sentences(text: str, *, min_chars: int = 120, max_chars: int = 900) -> str:
    """Оставляет только цельные предложения (без обрезков с краёв чанка)."""
    t = _fix_pss_ocr_glyphs(_repair_pss_ocr(text))
    if not t:
        return ""
    parts = re.split(r"(?<=[.!?…»])\s+", t)
    kept: list[str] = []
    for i, raw in enumerate(parts):
        s = raw.strip()
        if not s or len(s) < 35:
            continue
        if i == 0 and not _sentence_starts_clean(s):
            continue
        if i == len(parts) - 1 and not _sentence_ends_clean(s):
            continue
        if not _sentence_ends_clean(s):
            continue
        if re.search(r"-\s*$", s) or re.search(r"\s[а-яёa-z]{1,3}$", s.lower()):
            continue
        if _PSS_REGISTRY_RE.search(s) or _PSS_APPARATUS_RE.search(s):
            continue
        if _PSS_BAD_ABBR_RE.search(s) or _PSS_LATIN_GARBAGE_RE.search(s):
            continue
        kept.append(s)
    if not kept:
        return ""
    out = " ".join(kept)
    if len(out) > max_chars:
        acc: list[str] = []
        total = 0
        for s in kept:
            if total + len(s) + 1 > max_chars:
                break
            acc.append(s)
            total += len(s) + 1
        out = " ".join(acc)
    if len(out) < min_chars:
        return ""
    if out.count(".") + out.count("!") + out.count("?") < 1:
        return ""
    if not _is_pss_publishable(out):
        return ""
    return out


def _pss_chunk_quality(text: str) -> int:
    """Чем выше — тем лучше фрагмент для публикации."""
    t = _extract_complete_sentences(text)
    if not t:
        return -999
    if _pss_spell_issues(t):
        return -999
    score = 0
    n_sent = len(re.findall(r"[.!?…]", t))
    score += min(n_sent, 4) * 8
    if 140 <= len(t) <= 700:
        score += 12
    elif 700 < len(t) <= 900:
        score += 6
    if _sentence_starts_clean(t) and _sentence_ends_clean(t):
        score += 10
    if "¬" in text or re.search(r"[а-яё]-\s*$", text, re.I):
        score -= 20
    return score


def _clean_pss_excerpt(text: str) -> str:
    return _extract_complete_sentences(text)


def _pss_rag_excerpt(query: str) -> tuple[str, str] | None:
    """Цитата из ПСС (vector_db/lenin) без LLM."""
    db_path = _ROOT / "vector_db" / "lenin"
    if not db_path.is_dir():
        return None
    cfg = rubric_posts.load_json(_PSS_TOPICS_PATH) if _PSS_TOPICS_PATH.is_file() else {}
    forbidden = [x.lower() for x in (cfg.get("forbidden_in_chunk") or LENIN_CLICHE_PHRASES)]
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_huggingface import HuggingFaceEmbeddings

        emb = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        db = FAISS.load_local(str(db_path), emb, allow_dangerous_deserialization=True)
    except Exception:
        return None

    best_piece = ""
    best_cite = ""
    best_score = -999

    for d in db.similarity_search(query, k=48):
        raw = (d.page_content or "").strip()
        piece = _clean_pss_excerpt(raw)
        if not piece:
            continue
        low = piece.lower()
        if len(piece) < 120 or len(piece) > 900:
            continue
        if any(b in low for b in forbidden):
            continue
        sc = _pss_chunk_quality(raw)
        if sc <= best_score:
            continue
        src = d.metadata.get("source", "ПСС")
        pages = d.metadata.get("pages")
        cite = f"В.И. Ленин, {src}"
        if pages:
            cite += f", стр. {pages}"
        best_score = sc
        best_piece = piece
        best_cite = cite

    if best_score < 8 or not best_piece:
        return None
    return best_piece, best_cite


def _recent_bureaucracy_theme(recent_bodies: list[str]) -> bool:
    blob = " ".join(recent_bodies).lower()
    return any(
        x in blob
        for x in ("газет", "бюрократ", "канцеляр", "печать", "чиновник", "редакци")
    )


def _pick_pss_topic(*, recent_bodies: list[str] | None = None) -> dict | None:
    cfg = rubric_posts.load_json(_PSS_TOPICS_PATH)
    topics = cfg.get("topics") or []
    if not topics:
        return None
    used: dict = {}
    if _PSS_USED_PATH.is_file():
        try:
            used = json.loads(_PSS_USED_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            used = {}
    used_ids = set(used.get("ids") or [])
    pool = [
        t
        for t in topics
        if t.get("id") not in used_ids and t.get("id") not in PSS_TOPIC_DISABLED_IDS
    ] or [t for t in topics if t.get("id") not in PSS_TOPIC_DISABLED_IDS]
    if not pool:
        pool = list(topics)
    if recent_bodies and _recent_bureaucracy_theme(recent_bodies):
        filtered = [t for t in pool if t.get("id") not in PSS_TOPIC_COOLDOWN_IDS]
        if filtered:
            pool = filtered
    pick = random.choice(pool)
    ids = list(used_ids)
    ids.append(pick["id"])
    used["ids"] = ids[-24:]
    _PSS_USED_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PSS_USED_PATH.write_text(json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8")
    return pick


def build_pss_excerpt_post(*, recent_bodies: list[str] | None = None) -> tuple[str, str]:
    """Готовый вечерний пост: цитата ПСС + источник, без комментария канала."""
    topic_meta = _pick_pss_topic(recent_bodies=recent_bodies)
    if not topic_meta:
        return "[ПСС · фрагмент]", "Сегодня без выпуска — завтра снова фрагмент из ПСС."
    label = topic_meta.get("label", "ПСС")
    topic = f"[ПСС · фрагмент] {label} (id={topic_meta.get('id', '')})"
    hit = _pss_rag_excerpt(topic_meta.get("query", label))
    if not hit:
        return topic, ""
    quote, cite = hit
    body = (
        f"📜 <b>Фрагмент ПСС · {label}</b>\n\n"
        f"<blockquote>{quote}</blockquote>\n\n"
        f"<i>Источник: {cite}</i>\n\n"
        "#ленин #псс #история #мысль"
    )
    return topic, body


def is_prebuilt_evening_topic(topic_raw: str) -> bool:
    t = topic_raw or ""
    return any(
        x in t
        for x in (
            "[ПСС · фрагмент]",
            "[Сказка на ночь]",
            "[Ленин в литературе]",
            "[Ленин в искусстве]",
            "[Ленин · биография]",
            "[Ленин в кино]",
        )
    )


def requires_curated_photo(topic_raw: str) -> bool:
    """Посты, которые нельзя публиковать без фото."""
    t = topic_raw or ""
    return (
        is_curated_topic(t)
        or is_prebuilt_evening_topic(t)
        or "[#Вэтотдень]" in t
    )


async def resolve_lenin_slot(
    slot_value,
    *,
    weekday: int = 0,
    recent_bodies: list[str] | None = None,
) -> tuple[str, str | None, str | None, dict | None]:
    """(topic, prebuilt_text, image_path, rubric_seed)."""
    special = is_special_slot(slot_value)
    if special in ("channel_support", "weekly_support", "[SPECIAL:channel_support]"):
        topic, text = build_channel_support_post()
        return topic, text, None, None
    if special in ("lenin_calendar", "revolutionary_calendar", "[SPECIAL:lenin_calendar]"):
        topic, text = build_revolutionary_calendar_post()
        return topic, text, None, None
    if special in ("lenin_rubric", "curated_rubric", "[SPECIAL:lenin_rubric]"):
        explicit = None
        if isinstance(slot_value, dict):
            explicit = slot_value.get("rubric")
        return await build_rubric_slot(explicit, weekday=weekday)
    if special in ("lenin_pss", "pss_excerpt", "[SPECIAL:lenin_pss]"):
        topic, text = build_pss_excerpt_post(recent_bodies=recent_bodies)
        if not text or "blockquote" not in text:
            return topic, None, None, None
        return topic, text, None, None
    if special in ("lenin_book", "book_chunk", "[SPECIAL:lenin_book]"):
        topic, body = build_bedtime_story_post()
        if not body or "blockquote" not in body:
            return topic, None, None, None
        return topic, body, None, None
    if isinstance(slot_value, dict) and special == "lenin_marxist":
        angle = slot_value.get("angle") or slot_value.get("topic") or "современные события"
        return f"[Марксистский анализ] {angle}", None, None, None
    if isinstance(slot_value, str) and is_calendar_topic(slot_value):
        topic, text = build_revolutionary_calendar_post()
        return topic, text, None, None
    return "Свободная тема", None, None, None
