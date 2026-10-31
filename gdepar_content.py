"""Рубрики и спец-посты gdepar: разнообразие, литература, промо карты."""

from __future__ import annotations

import json
import logging
import os
import random
import re
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("empire.gdepar_content")

_ROOT = Path(__file__).resolve().parent
_ANGLE_FAMILIES_PATH = _ROOT / "data" / "gdepar_angle_families.json"
_LITERATURE_PATH = _ROOT / "data" / "gdepar_literature.json"
_CLASSIC_PATH = _ROOT / "data" / "gdepar_classic_banya.json"
_PROMO_PATH = _ROOT / "data" / "gdepar_promo_copy.json"
_LIT_HISTORY_PATH = _ROOT / "data" / "gdepar_literature_used.json"
_CLASSIC_HISTORY_PATH = _ROOT / "data" / "gdepar_classic_banya_used.json"
_CLASSIC_MEDIA_DIR = _ROOT / "media" / "gdepar" / "classic"
CLASSIC_RUBRIC_TAG = "[Классическая баня]"


def _load_json(path: Path) -> dict | list:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def extract_rubric(topic_raw: str) -> tuple[str | None, str]:
    m = re.match(r"\[(.*?)\]\s*(.*)", (topic_raw or "").strip(), re.DOTALL)
    if not m:
        return None, (topic_raw or "").strip()
    return m.group(1).strip(), m.group(2).strip()


def angle_families_for_text(text: str) -> set[str]:
    cfg = _load_json(_ANGLE_FAMILIES_PATH)
    if not isinstance(cfg, dict):
        return set()
    families = cfg.get("families", {})
    low = (text or "").lower()
    hit: set[str] = set()
    for fam_id, spec in families.items():
        kws = spec.get("keywords", []) if isinstance(spec, dict) else []
        if any(k in low for k in kws):
            hit.add(fam_id)
    return hit


# Клише без привязки к рубрике — триггер self-critique.
GDEPAR_CLICHE_PHRASES = (
    "тишина в парилке",
    "молчание в парной",
    "верхн",
    "полк",
    "лезь на верх",
    "замочи веник на 15",
    "замочить веник на 15",
    "алкоголь и давлен",
    "пиво после пар",
    "2–3 захода",
    "два-три захода",
    "температур",
    "градусов в парной",
)

# Нравоучения / «лекция Кириллычу» — не проходят self-critique.
GDEPAR_PREACHY_PHRASES = (
    "не геройств",
    "геройствуй",
    "сразу выходи",
    "немедленно выход",
    "пульс 14",
    "пульс выше",
    "без фанатизм",
    "не лезь на верх",
    "запомни:",
    "запомните:",
    "никогда не ",
    "ты обязан",
    "ты должен",
    "слушай, кириллыч",
    "кириллыч, слушай",
    "красные флаги без",
    "выходишь обновл",
    "очищение душ",
)


def topic_is_health_slot(topic_raw: str) -> bool:
    rubric, _ = extract_rubric(topic_raw or "")
    if not rubric:
        return False
    r = rubric.lower()
    return any(x in r for x in ("здоровь", "физиолог", "сердц", "давлен", "пульс"))


def preachy_findings(text: str, topic_raw: str = "") -> list[str]:
    """Нравоучительный тон — переписать в факты и цифры."""
    findings: list[str] = []
    if kirilych_template_opening(text):
        findings.append(
            "шаблон «Кириллыч, слушай» в начале — начни с факта или реплики Михалыча, без обращения"
        )
    low = (text or "").lower()
    hits = [ph for ph in GDEPAR_PREACHY_PHRASES if ph in low]
    if hits:
        findings.append(
            f"нравоучение/лекция ({hits[0]}…): только факты, цифры, 1–2 коротких совета — без «не геройствуй»"
        )
    imper = len(re.findall(r"(?m)^[^#\n]*\b(не |нельзя |запрещено |сразу |обязан)\b", low))
    if imper >= 4:
        findings.append("слишком много императивов подряд — сократи до 2 конкретных правил")
    if topic_is_health_slot(topic_raw):
        if "веник" in low and "веник" not in (topic_raw or "").lower():
            findings.append("тема про здоровье — убери веник и парение, оставь сердце/давление/заходы")
        if re.search(r"кириллыч.{0,40}(ты |ты,|слушай)", low):
            findings.append("не читай мораль Кириллычу — один нейтральный совет от Михалыча")
    return findings


def cliche_findings(text: str, topic_raw: str = "") -> list[str]:
    """Эвристики для второго прохода LLM."""
    findings: list[str] = []
    findings.extend(preachy_findings(text, topic_raw))
    low = (text or "").lower()
    rubric, body_topic = extract_rubric(topic_raw or "")
    topic_low = (body_topic or topic_raw or "").lower()
    for ph in GDEPAR_CLICHE_PHRASES:
        hit = ph in low or (ph.startswith("тишин") and "тишин" in low)
        if hit and ph not in topic_low and not (ph.startswith("тишин") and "тишин" in topic_low):
            if ph in ("верхн", "полк", "лезь на верх") and any(
                x in topic_low for x in ("полк", "верхн", "жар", "заход")
            ):
                continue
            if ph.startswith("тишин") and any(
                x in topic_low for x in ("тишин", "молчан", "психолог", "медитац")
            ):
                continue
            findings.append(f"клише вне темы слота: «{ph}»")
            break
    fam_text = angle_families_for_text(text)
    if len(fam_text) >= 2 and not rubric:
        findings.append("пост смешивает несколько семейств тем (полки+тишина+веник) — оставь один фокус")
    return findings


def family_penalty_score(recent_topic_texts: list[str], candidate: str) -> float:
    """Чем выше — тем хуже (семейство недавно использовалось)."""
    cand_fam = angle_families_for_text(candidate)
    if not cand_fam:
        return 0.0
    penalty = 0.0
    for t in recent_topic_texts:
        overlap = cand_fam & angle_families_for_text(t)
        if overlap:
            mult = 3.5 if "алкоголь_сердце" in overlap else 2.0
            penalty += mult * len(overlap)
    cliche_hits = sum(1 for ph in GDEPAR_CLICHE_PHRASES if ph in candidate.lower())
    penalty += 0.4 * cliche_hits
    return penalty


def pick_literature_entry() -> dict | None:
    data = _load_json(_LITERATURE_PATH)
    quotes = data.get("quotes", []) if isinstance(data, dict) else []
    if not quotes:
        return None
    used: dict = {}
    if _LIT_HISTORY_PATH.is_file():
        try:
            used = json.loads(_LIT_HISTORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            used = {}
    used_ids = set(used.get("ids", []))
    pool = [q for q in quotes if q.get("id") not in used_ids] or list(quotes)
    import random

    q = random.choice(pool)
    used_ids.add(q.get("id"))
    used["ids"] = list(used_ids)[-50:]
    used["last"] = datetime.utcnow().isoformat()
    _LIT_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LIT_HISTORY_PATH.write_text(json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8")
    return q


def build_literature_topic() -> str:
    q = pick_literature_entry()
    if not q:
        return "[Литература] Баня в русской прозе — цитата недели"
    return (
        f"[Литература] {q.get('author', '')}, «{q.get('work', '')}»: "
        f"{q.get('angle', 'баня в художественном тексте')}"
    )


def literature_prompt_block(topic_raw: str) -> str:
    """Блок для LLM: встроить цитату с атрибуцией."""
    data = _load_json(_LITERATURE_PATH)
    rubric, _ = extract_rubric(topic_raw)
    if rubric and rubric.lower() != "литература":
        return ""
    quotes = data.get("quotes", []) if isinstance(data, dict) else []
    q = None
    for item in quotes:
        if item.get("angle", "") in topic_raw or item.get("author", "") in topic_raw:
            q = item
            break
    if not q:
        q = pick_literature_entry()
    if not q:
        return ""
    return (
        f"\nОБЯЗАТЕЛЬНО В ПОСТЕ:\n"
        f"• Вставь цитату дословно (можно слегка сократить): «{q['text']}»\n"
        f"• Укажи источник: {q['author']}, {q['work']}\n"
        f"• 2–3 предложения комментария Михалыча к цитате — без морализаторства.\n"
        f"• НЕ повторяй банальности про верхнюю полку, алкоголь и тишину — это другие посты.\n"
    )




def _empire_db_path() -> Path:
    import os
    import re

    root = Path(__file__).resolve().parent
    default = root / "empire.db"
    if default.is_file():
        return default
    raw = os.getenv("DATABASE_URL", "").strip()
    if raw.startswith("sqlite"):
        m = re.search(r"sqlite(?:\+\w+)?:///(.+)$", raw)
        if m:
            rel = m.group(1).split("?")[0]
            if rel and rel != ":memory:":
                path = Path(rel)
                if not path.is_absolute():
                    path = root / rel
                if path.is_file():
                    return path
    return default


def pick_spot_for_tg_teaser() -> dict | None:
    """Случайная опубликованная баня с отзывом для TG ↔ карта."""
    import random
    import sqlite3

    db = _empire_db_path()
    if not db.is_file():
        return None
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT s.id, s.slug, s.title, s.city, s.region, s.rating_avg, s.heating, s.kind,
                   (SELECT r.text FROM banya_reviews r
                    WHERE r.spot_id = s.id AND r.status = 'approved' AND r.text IS NOT NULL
                    ORDER BY r.fetched_at DESC LIMIT 1) AS review_text,
                   (SELECT r.rating FROM banya_reviews r
                    WHERE r.spot_id = s.id AND r.status = 'approved' AND r.rating IS NOT NULL
                    ORDER BY r.fetched_at DESC LIMIT 1) AS review_rating
            FROM banya_spots s
            WHERE s.status = 'published' AND s.slug IS NOT NULL
              AND s.lat IS NOT NULL AND s.lon IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 24
            """
        ).fetchall()
        conn.close()
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("pick_spot_for_tg_teaser: %s", exc)
        return None
    if not rows:
        return None
    pool = [dict(r) for r in rows]
    with_review = [p for p in pool if (p.get("review_text") or "").strip()]
    return random.choice(with_review or pool)


def load_spot_by_slug(slug: str) -> dict | None:
    import sqlite3

    if not slug:
        return None
    db = _empire_db_path()
    if not db.is_file():
        return None
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT s.id, s.slug, s.title, s.city, s.region, s.rating_avg, s.heating, s.kind,
                   (SELECT r.text FROM banya_reviews r
                    WHERE r.spot_id = s.id AND r.status = 'approved' AND r.text IS NOT NULL
                    ORDER BY r.fetched_at DESC LIMIT 1) AS review_text,
                   (SELECT r.rating FROM banya_reviews r
                    WHERE r.spot_id = s.id AND r.status = 'approved' AND r.rating IS NOT NULL
                    ORDER BY r.fetched_at DESC LIMIT 1) AS review_rating
            FROM banya_spots s
            WHERE s.status = 'published' AND s.slug = ?
            LIMIT 1
            """,
            (slug,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def build_banya_week_topic() -> str:
    spot = pick_spot_for_tg_teaser()
    if not spot:
        return "[Баня недели] Карта gdepar.ru (fallback)"
    city = spot.get("city") or spot.get("region") or ""
    return f"[Баня недели] {spot.get('title', 'Баня')} · {city} (spot:{spot.get('slug', '')})"


def banya_week_prompt_block(topic_raw: str) -> str:
    if "[баня недели]" not in (topic_raw or "").lower():
        return ""
    m = re.search(r"spot:([\w\-]+)", topic_raw or "")
    spot = load_spot_by_slug(m.group(1)) if m else pick_spot_for_tg_teaser()
    if not spot:
        return (
            "\nСЛОТ [Баня недели]: карточка не найдена — коротко расскажи про gdepar.ru/map "
            "с UTM utm_campaign=banya_week.\n"
        )
    slug = spot.get("slug") or ""
    url = (
        f"https://gdepar.ru/banya/{slug}"
        f"?utm_source=telegram&utm_medium=post&utm_campaign=banya_week"
    )
    review = (spot.get("review_text") or "").strip()
    if review and len(review) > 220:
        review = review[:217] + "…"
    lines = [
        "\nСЛОТ [Баня недели] — ДИАЛОГ Михалыч ↔ Кириллыч (обязательно):",
        "• 2–4 коротких реплики: <b>Михалыч:</b> … <b>Кириллыч:</b> … (можно через тире, без «Кириллыч, слушай»).",
        "• Михалыч — пар, атмосфера, отзыв гостя; Кириллыч — факты: отопление, тип, район, цифры с карты.",
        "• Если есть цитата отзыва — в <blockquote>, не выдумывай отзыв.",
        f"• В конце одна строка со ссылкой на карточку: {url}",
        "ФАКТЫ С КАРТЫ (не выдумывать):",
        f"  Название: {spot.get('title', '')}",
        f"  Город/регион: {spot.get('city') or ''} / {spot.get('region') or ''}",
        f"  Рейтинг: {spot.get('rating_avg') or '—'}",
        f"  Отопление: {spot.get('heating') or '—'}, тип: {spot.get('kind') or '—'}",
    ]
    if review:
        lines.append(f"  Отзыв ({spot.get('review_rating') or '?'}★): «{review}»")
    lines.append("ЗАПРЕТ: не критикуй заведение без фактов; не выдумывай телефон и цены.\n")
    return "\n".join(lines) + "\n"


def duo_dialog_prompt_block(topic_raw: str) -> str:
    """Диалог двух голосов для практических слотов (не байка, не классика)."""
    low = (topic_raw or "").lower()
    if topic_is_bayka_slot(topic_raw) or CLASSIC_RUBRIC_TAG.lower() in low:
        return ""
    if "[баня недели]" in low or "promo_map" in low or "[печь и баня]" in low:
        return ""
    return (
        "\nФОРМАТ ДУЭТА Михалыч + Кириллыч (для этого поста):\n"
        "• Михалыч — традиция, пар, веник, этикет, «как в жизни».\n"
        "• Кириллыч — цифры, печь, вентиляция, материалы, «как устроено».\n"
        "• 1–2 коротких обмена репликами ИЛИ тезис Михалыча + уточнение Кириллыча.\n"
        "• НЕ начинай с шаблона «Кириллыч, слушай/смотри».\n"
        "• Раз в 2–3 поста — нативно: «на карте gdepar.ru смотрели…» (без агрессивного CTA).\n"
    )


def build_promo_map_post() -> tuple[str, str]:
    """Возвращает (topic_raw, готовый текст поста) — без LLM."""
    data = _load_json(_PROMO_PATH)
    variants = data.get("variants", []) if isinstance(data, dict) else []
    if not variants:
        body = (
            "🗺 <b>Где попариться рядом?</b>\n\n"
            "Карта бань на gdepar.ru — адрес, отзывы, район. Без суты с поиском.\n\n"
            "https://gdepar.ru/map?utm_source=telegram&utm_medium=post&utm_campaign=weekly_map"
        )
        return "[SPECIAL:promo_map]", body
    import random

    v = random.choice(variants)
    body = f"{v['headline']}\n\n{v['body']}\n\n{v['cta']}"
    return "[SPECIAL:promo_map]", body


def is_special_slot(slot_value) -> str | None:
    if isinstance(slot_value, dict):
        t = slot_value.get("type") or slot_value.get("special")
        if t:
            return str(t)
    if isinstance(slot_value, str) and slot_value.startswith("[SPECIAL:"):
        return slot_value
    return None



_KIRILYCH_LEAD_RE = re.compile(
    r"(?is)^"
    r"(\s*(?:<[^>]+>\s*)*|(?:[^\wа-яА-ЯёЁ]+\s*)?)"
    r"(?:кириллыч|михалыч)\s*[,—:\-–]\s*"
)


def kirilych_template_opening(text: str) -> bool:
    """Шаблонное обращение «Кириллыч, …» / «слушай, Кириллыч» — не лейбл «Кириллыч:»."""
    plain = re.sub(r"<[^>]+>", " ", text or "")
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        return False
    head = plain[:180]
    if re.search(r"(?i)\bслушай,?\s*кириллыч\b", head):
        return True
    # «Кириллыч, смотри» / «Кириллыч — слушай»; двоеточие = реплика диалога.
    if re.search(r"(?i)\bкириллыч\s*[,—\-–]\s*\S", head):
        return True
    return False


def kirilych_in_opening(text: str, *, window: int = 80) -> bool:
    plain = re.sub(r"<[^>]+>", "", text or "")
    return "кириллыч" in plain[:window].lower()


def strip_kirilych_opening(text: str) -> str:
    """Убирает обращение к Кириллычу/Михалычу в начале поста."""
    if not text:
        return text
    lines = text.strip().split("\n", 1)
    head = _KIRILYCH_LEAD_RE.sub(r"\1", lines[0], count=1)
    if len(lines) > 1:
        return f"{head}\n{lines[1]}".strip()
    return head.strip()


def normalize_body(text: str) -> str:
    """Нормализация текста поста для сравнения дублей."""
    s = (text or "").lower()
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"#\S+", " ", s)
    s = re.sub(r"[^a-zа-яё0-9]+", " ", s)
    tokens = [t for t in s.split() if len(t) > 2]
    return " ".join(tokens)


def body_jaccard(a: str, b: str) -> float:
    sa = set(normalize_body(a).split())
    sb = set(normalize_body(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def bodies_memory_hint(recent_bodies: list[str], *, threshold_note: float = 0.72) -> str:
    if not recent_bodies:
        return ""
    snippets = []
    for i, body in enumerate(recent_bodies[:5], 1):
        plain = re.sub(r"<[^>]+>", "", body or "")
        plain = " ".join(plain.split())
        snippets.append(f"  {i}) «{plain[:220]}…»" if len(plain) > 220 else f"  {i}) «{plain}»")
    joined = "\n".join(snippets)
    return (
        "\nПАМЯТЬ ТЕКСТОВ (критично): эти посты УЖЕ выходили в канале. "
        "Новый пост должен отличаться по формулировкам, примерам и структуре. "
        f"Если совпадение с любым из них выше ~{int(threshold_note * 100)}% по смыслу — это провал.\n"
        "Запрещено повторять: «верхняя полка», «тишина в парилке», «2–3 захода», «замочить веник», "
        "«температура в парной», «алкоголь и давление» — если это не единственная тема слота.\n"
        f"Недавние посты:\n{joined}\n"
        "Начни пост с ДРУГОЙ зацепки (не «Кириллыч, слушай» каждый раз одним и тем же).\n"
    )


def pick_classic_banya_entry() -> dict | None:
    data = _load_json(_CLASSIC_PATH)
    entries = data.get("entries", []) if isinstance(data, dict) else []
    if not entries:
        return None
    used: dict = {}
    if _CLASSIC_HISTORY_PATH.is_file():
        try:
            used = json.loads(_CLASSIC_HISTORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            used = {}
    last_by_id: dict[str, str] = dict(used.get("last_by_id") or {})
    now = datetime.utcnow()
    if not last_by_id and used.get("ids"):
        # Миграция со старого формата: id из истории считаем недавними.
        stamp = now.isoformat()
        for eid in used.get("ids") or []:
            if eid:
                last_by_id[str(eid)] = stamp
    cooldown = timedelta(days=56)

    def _eligible(entry: dict) -> bool:
        eid = entry.get("id") or ""
        ts = last_by_id.get(eid)
        if not ts:
            return True
        try:
            return now - datetime.fromisoformat(ts) >= cooldown
        except ValueError:
            return True

    pool = [e for e in entries if _eligible(e)]
    if not pool:
        # Все 160 недавно были — берём с самым старым last_by_id
        def _age(entry: dict) -> float:
            eid = entry.get("id") or ""
            ts = last_by_id.get(eid)
            if not ts:
                return float("inf")
            try:
                return (now - datetime.fromisoformat(ts)).total_seconds()
            except ValueError:
                return float("inf")

        pool = sorted(entries, key=_age, reverse=True)[: max(20, len(entries) // 4)]

    entry = random.choice(pool)
    eid = entry.get("id")
    if eid:
        last_by_id[eid] = now.isoformat()
    used_ids = list(last_by_id.keys())[-160:]
    used["ids"] = used_ids
    used["last_by_id"] = last_by_id
    used["last"] = now.isoformat()
    _CLASSIC_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CLASSIC_HISTORY_PATH.write_text(json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def format_classic_banya_post(entry: dict) -> str:
    import rubric_posts

    tag = entry.get("tag", "классика")
    return rubric_posts.format_curated_post(
        "Классическая баня",
        "📖",
        entry,
        hashtags=f"#баня #гдепар #{tag}",
        source_label="Источник",
        commentary_prefix="📖 <b>О чём писал автор:</b>",
        # До окт 2026: без школьного «сочинения» — только цитата + источник.
        show_commentary=False,
    )


_WIKI_UA = (
    "EmpireGdeparBot/1.1 (+https://gdepar.ru; contact: info@gdepar.ru) "
    "Python-httpx; classic-banya-rubric"
)

# URL/имя файла — отбраковка «баня вместо автора».
_PORTRAIT_REJECT_IN_URL = (
    "banya", "banja", "sauna", "bath", "steam", "paril", "парил", "бан",
    "wooden_architecture", "museum_of_wooden", "engraving", "гравюр",
    "interior", "интерьер",
)


def _portrait_url_ok(url: str) -> bool:
    low = (url or "").lower().split("?", 1)[0]
    if not low or not (url or "").lower().startswith("http"):
        return False
    if low.endswith((".svg", ".gif", ".tif", ".tiff")):
        return False
    return not any(x in low for x in _PORTRAIT_REJECT_IN_URL)


def _author_surname(author: str) -> str:
    """«С.Д. Довлатов» → «Довлатов». Пусто, если фамилии нет."""
    a = (author or "").strip()
    bare = re.sub(r"^[А-ЯA-Z](?:\.[А-ЯA-Z])*\s*", "", a).strip()
    parts = [p for p in (bare or a).split() if p]
    return parts[-1] if parts else ""


def _owner_marked_image(entry: dict) -> bool:
    """Файл из списка, который владелец отметил сам. Общая пачка image_file — не этот список."""
    raw = entry.get("image_approved")
    if raw is True:
        return True
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _wiki_page_is_author(title: str, author: str) -> bool:
    """Страница годится, только если в заголовке фамилия автора, а не сосед по поиску."""
    surname = _author_surname(author).lower().replace("ё", "е")
    if len(surname) < 3:
        return False
    page = (title or "").lower().replace("ё", "е")
    return surname in page


def _author_search_queries(author: str) -> list[str]:
    """Запросы: сначала фамилия + portrait, потом полное имя."""
    a = (author or "").strip()
    if not a:
        return []
    # «Ф.М. Достоевский» → «Достоевский»
    bare = re.sub(r"^[А-ЯA-Z](?:\.[А-ЯA-Z])*\s*", "", a).strip()
    parts = bare.split() if bare else a.split()
    surname = parts[-1] if parts else a
    out: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)

    add(f"{surname} portrait")
    add(f"{surname} портрет")
    add(f"{bare} portrait" if bare else f"{a} portrait")
    add(a)
    return out


def _classic_image_candidate_urls(entry: dict) -> list[str]:
    """Commons FilePath из image_file / image_url (курированные портреты)."""
    from urllib.parse import quote

    out: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        u = (u or "").strip()
        if u and u not in seen and _portrait_url_ok(u):
            seen.add(u)
            out.append(u)

    raw_file = (entry.get("image_file") or "").strip()
    if not raw_file and entry.get("image_url"):
        tail = str(entry["image_url"]).rsplit("/", 1)[-1]
        if tail.startswith(("440px-", "640px-", "320px-")):
            raw_file = tail.split("-", 1)[-1]
        elif tail and "." in tail:
            raw_file = tail
    if raw_file:
        enc = quote(raw_file.replace(" ", "_"), safe="/")
        add(f"https://commons.wikimedia.org/wiki/Special:FilePath/{enc}?width=800")
    add(entry.get("image_url") or "")
    return out


async def _download_classic_image(url: str, dest: Path) -> bool:
    import httpx

    headers = {"User-Agent": _WIKI_UA, "Accept": "image/*,*/*;q=0.8"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200 or len(r.content) < 2048:
            return False
        ctype = (r.headers.get("content-type") or "").lower()
        if "html" in ctype and "image" not in ctype:
            return False
        dest.write_bytes(r.content)
        return dest.stat().st_size >= 2048


def classic_image_rel_path(entry: dict) -> str:
    """Относительный путь для PostDraft.image_path и /media на сайте."""
    eid = (entry.get("id") or "classic").strip()
    return f"media/gdepar/classic/{eid}.jpg"


def _author_portrait_search_terms(author: str) -> list[str]:
    return _author_search_queries(author)


async def _commons_file_urls_for_search(query: str, *, limit: int = 8) -> list[str]:
    """Поиск файлов на Wikimedia Commons; только URL, прошедшие _portrait_url_ok."""
    import httpx
    from urllib.parse import quote

    api = (
        "https://commons.wikimedia.org/w/api.php"
        f"?action=query&list=search&srsearch={quote(query)}"
        f"&srnamespace=6&format=json&srlimit={limit}&origin=*"
    )
    headers = {"User-Agent": _WIKI_UA}
    out: list[str] = []
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
            r = await client.get(api, headers=headers)
            if r.status_code != 200:
                return out
            data = r.json()
            for hit in (data.get("query") or {}).get("search", []):
                title = hit.get("title") or ""
                if not title.startswith("File:"):
                    continue
                fname = title[5:].replace(" ", "_")
                enc = quote(fname, safe="/")
                url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{enc}?width=800"
                if _portrait_url_ok(url) and _portrait_url_ok(fname):
                    out.append(url)
    except Exception as exc:
        logger.warning("commons search %r: %s", query, type(exc).__name__)
    return out


async def fetch_wikipedia_author_portrait(author: str, dest: Path) -> bool:
    """Портрет с ru.wikipedia (pageimages)."""
    import httpx
    from urllib.parse import quote

    headers = {"User-Agent": _WIKI_UA}
    a = (author or "").strip()
    bare = re.sub(r"^[А-ЯA-Z](?:\.[А-ЯA-Z])*\s*", "", a).strip()
    wiki_queries: list[str] = []
    for q in (a, bare):
        if q and q not in wiki_queries:
            wiki_queries.append(q)

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=14.0) as client:
            for q in wiki_queries:
                search_url = (
                    "https://ru.wikipedia.org/w/api.php?action=query&list=search"
                    f"&srsearch={quote(q)}&utf8=&format=json&srlimit=6"
                )
                r = await client.get(search_url, headers=headers)
                if r.status_code != 200:
                    continue
                for hit in (r.json().get("query") or {}).get("search", []):
                    title = hit.get("title") or ""
                    if "значения)" in title.lower():
                        continue
                    # Не брать первую иллюстрацию выдачи: у Довлатова нет pageimage,
                    # и следующим файлом оказывается чужой портрет (Берберова).
                    if not _wiki_page_is_author(title, author):
                        continue
                    img_api = (
                        "https://ru.wikipedia.org/w/api.php?action=query"
                        f"&titles={quote(title)}&prop=pageimages&format=json"
                        "&piprop=original|thumbnail&pithumbsize=800"
                    )
                    ir = await client.get(img_api, headers=headers)
                    if ir.status_code != 200:
                        continue
                    pages = (ir.json().get("query") or {}).get("pages", {})
                    for page in pages.values():
                        src = (page.get("original") or {}).get("source") or (
                            (page.get("thumbnail") or {}).get("source")
                        )
                        if not src or not _portrait_url_ok(src):
                            continue
                        if await _download_classic_image(src, dest):
                            logger.info("classic wiki portrait %s <- %s", author, title)
                            return True
    except Exception as exc:
        logger.warning("wiki portrait %r: %s", author, type(exc).__name__)
    return False


async def _author_portrait_urls(entry: dict) -> list[str]:
    """Портрет автора с Commons (только portrait-запросы, без «баня»)."""
    author = (entry.get("author") or "").strip()
    urls: list[str] = []
    seen: set[str] = set()
    for q in _author_search_queries(author):
        for u in await _commons_file_urls_for_search(f'"{q}"', limit=6):
            if u not in seen:
                seen.add(u)
                urls.append(u)
        if urls:
            break
    return urls


def classic_image_abs_path(entry: dict) -> Path:
    eid = (entry.get("id") or "classic").strip()
    return _CLASSIC_MEDIA_DIR / f"{eid}.jpg"


async def ensure_classic_image(entry: dict) -> str | None:
    """Портрет автора.

    Автомат — только страница Википедии, в заголовке которой есть фамилия.
    Иначе файл только если владелец поставил image_approved.
    Кэш на диске без этой отметки не отдаём: там уже оказывалась Берберова.
    """
    eid = (entry.get("id") or "classic").strip()
    rel = classic_image_rel_path(entry)
    _CLASSIC_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    dest = classic_image_abs_path(entry)

    tried: set[str] = set()

    async def try_urls(urls: list[str]) -> bool:
        for url in urls:
            if not url or url in tried:
                continue
            tried.add(url)
            try:
                if await _download_classic_image(url, dest):
                    return True
            except Exception as exc:
                logger.warning("classic image %s url fail: %s", eid, type(exc).__name__)
        return False

    if _owner_marked_image(entry):
        if dest.is_file() and dest.stat().st_size > 2048:
            return rel
        if await try_urls(_classic_image_candidate_urls(entry)):
            return rel
        logger.warning("classic marked image missing for %s", eid)
        return None

    if dest.is_file():
        dest.unlink()
    if await fetch_wikipedia_author_portrait(entry.get("author") or "", dest):
        return rel
    logger.warning("classic portrait missing for %s (%s)", eid, entry.get("author"))
    return None


async def build_classic_banya_post() -> tuple[str, str, str | None]:
    """(topic_raw, html_text, image_path) — без LLM."""
    entry = pick_classic_banya_entry()
    if not entry:
        body = (
            "📖 <b>Классическая баня</b>\n\n"
            "Сегодня без цитаты — завтра снова из русской прозы.\n\n"
            "#баня #гдепар #классика"
        )
        return f"{CLASSIC_RUBRIC_TAG} fallback", body, None
    topic = (
        f"{CLASSIC_RUBRIC_TAG} {entry.get('author', '')}, {entry.get('work', '')} "
        f"(id={entry.get('id', '')})"
    )
    text = format_classic_banya_post(entry)
    img = await ensure_classic_image(entry)
    return topic, text, img


async def resolve_gdepar_slot(slot_value, *, resolve_topic_fn) -> tuple[str, str | None, str | None]:
    """
    Возвращает (topic_for_llm, prebuilt_text, prebuilt_image_path).
  prebuilt_text != None → публиковать как есть (промо, классика).
    """
    special = is_special_slot(slot_value)
    if special in ("promo_map", "weekly_promo", "[SPECIAL:promo_map]"):
        topic, text = build_promo_map_post()
        return topic, text, None
    if special in ("classic_banya", "classic", "[SPECIAL:classic_banya]"):
        return await build_classic_banya_post()
    import gdepar_book_rubrics as gbr

    book_key = gbr.is_book_rubric_slot(slot_value)
    if book_key:
        return await gbr.build_book_rubric_post(book_key)
    if special in ("literature", "lit", "[SPECIAL:literature]"):
        topic = build_literature_topic()
        return topic, None, None
    if special in ("banya_week", "[SPECIAL:banya_week]"):
        return build_banya_week_topic(), None, None
    import gdepar_mono_curated as gmono
    import gdepar_duo_curated as gduo

    if gmono.is_mono_curated_slot(slot_value):
        return await gmono.build_mono_curated_slot(pool=gmono.pool_from_slot(slot_value))
    if gduo.is_duo_curated_slot(slot_value):
        return await gduo.build_duo_curated_slot(pool=gduo.pool_from_slot(slot_value))
    topic = await resolve_topic_fn("gdepar", slot_value)
    return topic, None, None


# Промпты Nano Banana / Gemini — ваши тексты (скрины 2026-05).
GDEPAR_VENIK_BIRCH_GEMINI_PROMPT = (
    "A traditional birch sauna whisk (banya venik), made of fresh green birch branches and "
    "leaves tied together at the handle with natural twine. The whisk is lying on a wet wooden "
    "sauna bench. Rising steam, warm rustic wooden background, water droplets on the leaves. "
    "Hyper-realistic, macro photography, cinematic lighting, highly detailed, 8k."
)
GDEPAR_VENIK_OAK_GEMINI_PROMPT = (
    "A sturdy oak banya venik, dense broad green oak leaves bound firmly at the base. "
    "Lying on rustic wooden planks in a steamy sauna environment. Soft warm amber ambient light, "
    "authentic traditional sauna atmosphere, photorealistic, shallow depth of field, 8k resolution."
)
GDEPAR_VENIK_JUNIPER_GEMINI_PROMPT = (
    "A traditional juniper banya venik (sauna whisk), dense green juniper twigs with needles, "
    "bound firmly at the base with natural twine. Lying on wet wooden sauna bench, rising steam, "
    "warm amber light, photorealistic, shallow depth of field, 8k, authentic Russian banya."
)
GDEPAR_VENIK_GEMINI = {
    "model": "gemini-2.5-flash-image",
    "aspect_ratio": "4:3",
    "image_size": "1K",
}

# Канонические промпты fal/flux для банных веников (редактор, 2026-05).
# Типичный провал Flux: пучок однотолщинных зелёных «травинок» + отдельная деревянная
# ручка (как на кухонной щётке). Якоря: ВЕЕР из ВЕТОК С ЛИСТЬЯМИ, хват = пучок стволиков.
_GDEPAR_VENIK_PHOTO = (
    "Professional still-life photograph, 85mm lens, shallow depth of field. "
    "Traditional Russian wooden banya (parilka), wet dark larch bench, soft steam, "
    "blurred stove glow, warm amber light, water droplets."
)
_GDEPAR_VENIK_GRIP = (
    "Binding: rough birch-bark twine or hemp at the thick end only. "
    "Grip is a short dense stub (8–12 cm) of the SAME bundled twig stems — "
    "NOT a separate piece of wood, NOT a lathe-turned handle, NOT a dowel, NOT a rod, "
    "NOT a tool stick, NOT a brush handle, NOT a mop handle."
)
_GDEPAR_VENIK_SHAPE = (
    "Object: Russian banya venik (venik dlya parenya, sauna whisk for parenie) — "
    "a flat wide triangular FAN 35–45 cm across, 3–5 cm thick, lying horizontally on the bench. "
    "NOT a round bouquet, NOT a narrow vertical bundle, NOT a vase arrangement, NOT a broom."
)
_GDEPAR_VENIK_ANTIGRASS = (
    "Every twig has foliage along its length; leaves overlap across the whole fan. "
    "NOT bare green rods, NOT uniform cylindrical grass stalks, NOT chives, NOT onion greens, "
    "NOT lemongrass, NOT reeds, NOT bamboo shoots, NOT a decorative herb brush, "
    "NOT leaves clustered only at the base with naked stems above."
)

GDEPAR_VENIK_BIRCH_IMAGE_PROMPT = (
    f"{_GDEPAR_VENIK_PHOTO} "
    f"{_GDEPAR_VENIK_SHAPE} "
    "Fresh birch banya venik: dozens of overlapping Betula birch branches, each branch "
    "carrying small green serrated triangular birch leaves from base to tip. "
    f"{_GDEPAR_VENIK_ANTIGRASS} "
    f"{_GDEPAR_VENIK_GRIP} "
    "Looks like a real venik from a Russian banya market before the first steaming. "
    "NOT a herb bouquet, NOT tea leaves, NOT eucalyptus, NOT a household broom."
)
GDEPAR_VENIK_OAK_IMAGE_PROMPT = (
    f"{_GDEPAR_VENIK_PHOTO} "
    f"{_GDEPAR_VENIK_SHAPE} "
    "Fresh oak banya venik: dozens of overlapping oak branches with broad lobed deep-green "
    "oak leaves densely packed across the entire fan. "
    f"{_GDEPAR_VENIK_ANTIGRASS} "
    f"{_GDEPAR_VENIK_GRIP} "
    "Real Russian oak venik for parenie on wet rustic planks. "
    "NOT herbs, NOT tea, NOT a broom, NOT a floral bouquet."
)
GDEPAR_VENIK_NEGATIVE_EXTRA = (
    "grass bundle, grass stalks, chives, onion greens, lemongrass, reed bundle, bamboo whisk, "
    "uniform thin green cylinders, bare green rods, naked stems, stems without leaves, "
    "leaves only at base, decorative green brush, kitchen herb brush, sage bundle, mint bouquet, "
    "parsley, cilantro, herb bouquet, tea leaves, culinary herbs, spice bundle, floral arrangement, "
    "ikebana, single twig, single branch, loose leaves, eucalyptus, olive branch, tropical plant, "
    "wooden dowel, wooden rod, lathe-turned handle, turned wood handle, stick handle, tool handle, "
    "brush handle, paintbrush, scrub brush, bottle brush, wand, mop stick, long handle, "
    "pine needles only, fir sprig, spruce twig, conifer decoration, straw broom, witch broom, "
    "household broom, kitchen broom, metal handle, brass ferrule, copper pipe, plastic leaves, "
    "artificial plant, person, hands, text, watermark"
)
# Только для веников: больше шагов и чуть выше guidance (см. main.generate_image).
GDEPAR_VENIK_FLUX = {
    "num_inference_steps": 42,
    "guidance_scale": 5.5,
    "image_size": "landscape_4_3",
}

GDEPAR_HEALTH_IMAGE_PROMPT = (
    "Traditional Russian wooden banya interior: steam, bench, wooden bucket and ladle, "
    "soft warm light through small window, empty room, no people, no broom, no whisk, no plants, "
    "photorealistic, 8k"
)

# Только тема слота — не LLM-промпт (там часто «whisk» на любой пост про баню).
_RE_VENIK_TOPIC = re.compile(
    r"(?i)(веник|venik|парени|запарив|можжевельник|\[веники\])"
)
_RE_HEALTH_TOPIC = re.compile(r"(?i)\[(здоровь|физиолог)")
_RE_VENIKI_RUBRIC = re.compile(r"(?i)\[веники\]")
_RE_OAK_VENIK = re.compile(r"(?i)\b(дуб|дубов|oak)\b")
_RE_BIRCH_VENIK = re.compile(r"(?i)\b(бер[ёе]з|берез|birch)\b")
_RE_JUNIPER_VENIK = re.compile(r"(?i)(можжевельник|juniper)")

GDEPAR_VENIK_JUNIPER_IMAGE_PROMPT = (
    f"{_GDEPAR_VENIK_PHOTO} "
    f"{_GDEPAR_VENIK_SHAPE} "
    "Fresh juniper banya venik: wide fan of many thin juniper twigs with short green needles "
    "along each branch, densely packed — NOT a single decorative pine sprig. "
    f"{_GDEPAR_VENIK_GRIP} "
    "NOT herbs, NOT grass stalks, NOT a broom, NOT a turned wood handle."
)

GDEPAR_STOVE_IMAGE_PROMPT = (
    "Close-up of a Russian bath stove (pechka) with smooth river stones on top, "
    "glowing embers behind a cast-iron door, wooden sauna interior, steam wisps, "
    "photorealistic, warm amber light, no people, 8k."
)

GDEPAR_SAUNA_SCENE_PROMPT = (
    "Interior of a traditional Russian wooden banya: steam-filled room, wooden benches, "
    "copper water bucket and ladle, soft warm light through small window, no people, "
    "no brooms, photorealistic, cinematic, 8k."
)


def venik_image_provider() -> str:
    """flux | gemini. auto → gemini при GEMINI_API_KEY, иначе flux."""
    raw = (os.getenv("GDEPAR_VENIK_IMAGE_PROVIDER") or "auto").strip().lower()
    if raw in ("gemini", "nano", "nanobanana", "nb", "google"):
        return "gemini"
    if raw == "flux":
        return "flux"
    key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY") or "").strip()
    return "gemini" if key else "flux"


def _venik_kind(topic_raw: str) -> str | None:
    blob = (topic_raw or "").strip()
    if not blob:
        return None
    if not (_RE_VENIK_TOPIC.search(blob) or _RE_VENIKI_RUBRIC.search(blob)):
        return None
    if _RE_JUNIPER_VENIK.search(blob) and not _RE_OAK_VENIK.search(blob):
        return "juniper"
    if _RE_OAK_VENIK.search(blob) and not _RE_BIRCH_VENIK.search(blob):
        return "oak"
    return "birch"


def resolve_venik_image_prompt(
    topic_raw: str = "",
    provider: str | None = None,
    *_ignored_llm: str,
) -> str | None:
    """EN-промпт для обложки — только если в ТЕМЕ слота есть веник / [Веники]."""
    kind = _venik_kind(topic_raw)
    if not kind:
        return None
    prov = (provider or venik_image_provider()).strip().lower()
    if prov == "gemini":
        return {
            "birch": GDEPAR_VENIK_BIRCH_GEMINI_PROMPT,
            "oak": GDEPAR_VENIK_OAK_GEMINI_PROMPT,
            "juniper": GDEPAR_VENIK_JUNIPER_GEMINI_PROMPT,
        }[kind]
    return {
        "birch": GDEPAR_VENIK_BIRCH_IMAGE_PROMPT,
        "oak": GDEPAR_VENIK_OAK_IMAGE_PROMPT,
        "juniper": GDEPAR_VENIK_JUNIPER_IMAGE_PROMPT,
    }[kind]


def resolve_gdepar_image_prompt(
    topic_raw: str = "",
    provider: str | None = None,
    *_ignored_llm: str,
) -> str | None:
    """Канонический EN-промпт: только по теме слота (не по PROMPT от LLM)."""
    topic = (topic_raw or "").strip()
    if not topic:
        return None
    venik = resolve_venik_image_prompt(topic, provider=provider)
    if venik:
        return venik
    low = topic.lower()
    if _RE_HEALTH_TOPIC.search(topic):
        return GDEPAR_HEALTH_IMAGE_PROMPT
    if re.search(r"(?i)\[печи\]|камн|печк|камен", low):
        return GDEPAR_STOVE_IMAGE_PROMPT
    if re.search(r"(?i)\[ароматерапия\]", low):
        return GDEPAR_SAUNA_SCENE_PROMPT
    if re.search(r"(?i)\[гастроном", low):
        return GDEPAR_SAUNA_SCENE_PROMPT
    return GDEPAR_SAUNA_SCENE_PROMPT


def filter_hashtags_for_topic(topic_raw: str, tags: list[str]) -> list[str]:
    """Убрать #Веник и т.п., если слот не про веник."""
    if not tags:
        return tags
    low = (topic_raw or "").lower()
    venik_ok = bool(_RE_VENIK_TOPIC.search(low) or _RE_VENIKI_RUBRIC.search(low))
    out: list[str] = []
    for t in tags:
        tl = t.lower().lstrip("#")
        if not venik_ok and tl in ("веник", "venik", "парение") and "здоровь" in low:
            continue
        if not venik_ok and tl == "веник":
            continue
        out.append(t)
    return out


def health_topic_prompt_block(topic_raw: str) -> str:
    if not topic_is_health_slot(topic_raw):
        return ""
    return (
        "\nСЛОТ [Здоровье/физиология] — ФОРМАТ (жёстко):\n"
        "• 2–4 коротких абзаца: цифра или порог → что делать → один запрет.\n"
        "• Без нравоучений («не геройствуй», «ты обязан», «слушай, Кириллыч»).\n"
        "• Не упоминай веник, запаривание, «веером по спине», если тема не про веник.\n"
        "• ПРОМПТ для картинки: wooden banya interior, steam, bucket — без whisk/broom/venik.\n"
    )


def topic_is_bayka_slot(topic_raw: str) -> bool:
    low = (topic_raw or "").lower()
    return "[байка" in low or "предбанник" in low or "банник" in low


def bayka_prompt_block(topic_raw: str) -> str:
    if not topic_is_bayka_slot(topic_raw):
        return ""
    return (
        "\nСЛОТ [Байка в предбаннике] — ФОРМАТ (жёстко):\n"
        "• 220–380 слов: одна бытовая история из бани или предбанника, без пафоса.\n"
        "• Голос: Михалыч рассказывает от себя или «деда / приятеля / соседа» — не «генерал N», "
        "не «1943-й под Сталинградом», не выдуманные фронтовые легенды без источника.\n"
        "• Детали: пар, полок, ведро, запах дуба/берёзы, смех, ошибка новичка, смешной случай — "
        "конкретика, не comic book.\n"
        "• ЗАПРЕТ: «веник как каска», «мораль? да хрен её знает», «до Берлина дошёл в вещмешке», "
        "«лист дубовый от осколков», бомбёжки и война как декорация.\n"
        "• Финал: одна короткая бытовая мысль или шутка — без нравоучения и без «выходишь обновлённым».\n"
        "• Не обращайся «Кириллыч, ты ж любишь байки» — сразу в историю.\n"
        "• ПРОМПТ для картинки: Russian banya antechamber, steam, wooden bench, warm light — без war.\n"
    )
