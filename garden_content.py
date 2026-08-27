"""Спец-посты канала Garden: промо бота, лунный посевной календарь (без LLM)."""

from __future__ import annotations

import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from garden_links import garden_bot_link

_MSK = ZoneInfo("Europe/Moscow")
_ROOT = Path(__file__).resolve().parent
_PROMO_PATH = _ROOT / "data" / "garden_promo_copy.json"
_CALENDAR_PATH = _ROOT / "data" / "garden_kizima_calendar.json"
_CALENDAR_USED_PATH = _ROOT / "data" / "garden_kizima_calendar_used.json"

_MONTHS_RU = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)
_KIZIMA_SOURCE_MARKERS = (
    "кизима",
    "календар",
    "лунн",
    "5000 советов",
    "лунный посевной",
    "шпаргалка садовода",
)
# Общая теория из книги — не «совет на день».
_KIZIMA_THEORY_MARKERS = (
    "уверяю",
    "объясняю",
    "фотосинтез",
    "гравитац",
    "притяжени",
    "опроверг",
    "корневая система",
    "минимальна",
    "период растущей луны",
    "полнолуния и",
)
_ACTION_MARKERS = (
    "посе",
    "посад",
    "высад",
    "полив",
    "пропол",
    "окуч",
    "собир",
    "убор",
    "внес",
    "подкорм",
    "укры",
    "расса",
    "гряд",
    "тепли",
    "парник",
    "чеснок",
    "картоф",
    "томат",
    "огурц",
)

LUNAR_IMAGE_PROMPT = (
    "Soft evening sky with visible moon phase over a Russian kitchen garden in late spring, "
    "vegetable beds and green seedlings, natural light, photorealistic, no people, no text, 8k"
)


def is_special_slot(slot_value) -> str | None:
    if isinstance(slot_value, dict):
        t = slot_value.get("type") or slot_value.get("special")
        if t:
            return str(t)
    return None


def build_bot_promo_post() -> tuple[str, str]:
    """(topic_raw, готовый текст поста)."""
    variants = []
    if _PROMO_PATH.is_file():
        data = json.loads(_PROMO_PATH.read_text(encoding="utf-8"))
        variants = data.get("variants", [])
    if not variants:
        body = "🌱 Материалы Степаныча — в боте канала."
        link = garden_bot_link("weekly")
        if link:
            body += f"\n\n{link}"
        return "[SPECIAL:bot_promo]", body
    v = next(
        (x for x in variants if "семь косяков" in (x.get("headline") or "").lower()),
        variants[0],
    )
    body = f"{v['headline']}\n\n{v['body']}"
    link = garden_bot_link("weekly_post")
    if link:
        body += f"\n\n👉 {link}"
    else:
        body += "\n\n👉 Ссылка на бот — в закрепе канала."
    return "[SPECIAL:bot_promo]", body


def _load_calendar_entries() -> list[dict]:
    if not _CALENDAR_PATH.is_file():
        return []
    data = json.loads(_CALENDAR_PATH.read_text(encoding="utf-8"))
    return list(data.get("entries") or [])


def _explicit_day_entry(when: datetime) -> dict | None:
    candidates = [
        e
        for e in _load_calendar_entries()
        if e.get("month") == when.month and e.get("day") == when.day
    ]
    if not candidates:
        return None

    def _score(e: dict) -> int:
        src = (e.get("source") or "").lower()
        book = src.split("(", 1)[-1].rstrip("…)").lower() if "(" in src else src
        text = (e.get("text") or "").lower()
        s = 0
        if "лунный" in book and "календар" in book:
            s += 14
        elif "шпаргалка" in book:
            s += 6
        if str(when.year) in str(e.get("year", "")):
            s += 3
        if any(w in text for w in ("посев", "посад", "полив", "гряд", "парник", "тепли", "окуч", "пропол")):
            s += 10
        berry = any(w in text for w in ("ягод", "мускат", "грозд", "зимостойк", "кисти по", "созрев"))
        if berry:
            # В «фазы + работы» ягодники — нормальный совет на день, не отбрасываем дату.
            if "фазы + работы" in src:
                s -= 2
            else:
                s -= 20
        return s

    best = max(candidates, key=_score)
    sc = _score(best)
    if sc >= 8:
        return best
    src = (best.get("source") or "").lower()
    if sc >= 6 and "фазы + работы" in src and str(when.year) == str(best.get("year", "")):
        return best
    return None


def _kizima_rag_chunks(when: datetime, k: int = 4) -> list[tuple[str, str]]:
    """(source, text) из vector_db/garden, только календари Кизимы."""
    db_path = _ROOT / "vector_db" / "garden"
    if not db_path.is_dir():
        return []
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_huggingface import HuggingFaceEmbeddings

        emb = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        db = FAISS.load_local(str(db_path), emb, allow_dangerous_deserialization=True)
    except Exception:
        return []

    q = (
        f"лунный посевной календарь {when.day} {_MONTHS_RU[when.month - 1]} "
        f"фаза луны посев посадка полив что делать огородник"
    )
    docs = db.similarity_search(q, k=k * 3)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for d in docs:
        src = (d.metadata.get("source") or "").lower()
        if not any(m in src for m in _KIZIMA_SOURCE_MARKERS):
            continue
        piece = re.sub(r"\s+", " ", (d.page_content or "").strip())
        if len(piece) < 80 or piece in seen:
            continue
        seen.add(piece)
        out.append((d.metadata.get("source", "Кизима"), piece[:900]))
        if len(out) >= k:
            break
    return out


_OCR_STOP_WORDS = frozenset({
    "и", "в", "во", "на", "по", "не", "ни", "из", "за", "от", "до", "под", "над", "без",
    "для", "при", "что", "как", "или", "но", "а", "с", "к", "у", "о", "об", "со", "ко",
    "то", "же", "бы", "ли", "он", "она", "они", "мы", "вы", "я", "ты", "это", "тот",
})


def _repair_ocr_spaces(text: str) -> str:
    """Склейка разорванных OCR-слов («корнепло ды»), без смерти нормального текста."""
    if not text:
        return text
    t = re.sub(r"-\s+", "", text)
    if _text_looks_squashed(t):
        t = re.sub(r"\s+", " ", t).strip()
        return t
    pat = re.compile(r"([а-яё-]{3,})\s+([а-яё]{1,4})\b", re.I)

    def _join(m: re.Match[str]) -> str:
        left, right = m.group(1), m.group(2)
        if right.lower() in _OCR_STOP_WORDS:
            return m.group(0)
        if "-" in left and right.islower():
            return left + right
        if left[-1].isupper() or right[0].isupper():
            return m.group(0)
        if not left[-1].islower() or not right.islower():
            return m.group(0)
        return left + right

    t = pat.sub(_join, t)
    return re.sub(r"\s+", " ", t).strip()


def _chunk_is_actionable(piece: str) -> bool:
    low = piece.lower()
    if len(piece) < 60:
        return False
    if any(m in low for m in _KIZIMA_THEORY_MARKERS):
        return False
    if len(piece) > 420 and not any(m in low for m in _ACTION_MARKERS):
        return False
    if piece.count(".") < 1 and len(piece) > 200:
        return False
    return True


def _score_rag_chunk(piece: str, when: datetime) -> int:
    low = piece.lower()
    score = 0
    if any(m in low for m in _ACTION_MARKERS):
        score += 12
    if any(m in low for m in _KIZIMA_THEORY_MARKERS):
        score -= 25
    if str(when.day) in piece or _MONTHS_RU[when.month - 1][:3] in low:
        score += 8
    if 80 <= len(piece) <= 380:
        score += 5
    if len(piece) > 550:
        score -= 8
    return score


def _text_looks_squashed(text: str) -> bool:
    """PDF без пробелов: «изньсвоимрастениям», «Длякаждогомесяца…»."""
    if not text:
        return False
    if re.search(r"[а-яёА-ЯЁ]{18,}", text):
        return True
    if len(text) > 100 and text.count(" ") < len(text) / 35:
        return True
    return False


def _clean_rag_excerpt(text: str) -> str:
    """Убрать оглавление и мусор OCR, оставить совет."""
    t = _repair_ocr_spaces(text.strip())
    if _text_looks_squashed(t):
        return ""
    if len(t) > 400 and t.count(".") < 2:
        return ""
    if not _chunk_is_actionable(t):
        return ""
    return t


def _pick_best_kizima_chunk(when: datetime) -> tuple[str, str] | None:
    """Один лучший фрагмент RAG, не три blockquote подряд."""
    best: tuple[str, str] | None = None
    best_score = -999
    for src, piece in _kizima_rag_chunks(when, k=8):
        cleaned = _clean_rag_excerpt(piece)
        if not cleaned:
            continue
        sc = _score_rag_chunk(cleaned, when)
        if sc > best_score:
            best_score = sc
            best = (src, cleaned)
    if best_score < 4:
        return None
    return best


def _polish_lunar_body(text: str) -> str:
    """OCR, обрезки «…» и хвост « а» в строке календаря."""
    raw = (text or "").strip()
    body = _repair_ocr_spaces(raw)
    body = re.sub(r"\s*Кизимой", "", body, flags=re.I)
    body = re.sub(r"календарю\s+Кизимой", "календарю", body, flags=re.I)
    body = re.sub(r"\s+", " ", body).strip()
    if body.endswith("…") or body.endswith("..."):
        body = body.rstrip(".… ")
    if re.search(r"\s[аa]$", body):
        body = re.sub(r"\s[аa]$", "", body).rstrip("–—,;") + "."
    if body and body[-1] not in ".!?":
        body += "."
    if _text_looks_squashed(body) and not _text_looks_squashed(raw):
        body = raw.rstrip(".… ")
        if body and body[-1] not in ".!?":
            body += "."
    if _text_looks_squashed(body):
        return ""
    return body


def _fallback_lunar_body(when: datetime) -> str:
    """Если в базе нет строки на дату — честный совет без мусорного RAG."""
    return (
        f"На {when.day} {_MONTHS_RU[when.month - 1]} отдельной строки в лунном календаре нет. "
        "Сверьте фазу Луны в посевном календаре — это важнее общих лекций про корнеплоды. "
        "Практика: одно действие по луне — посев, посадка или уход; без перегруза грядки."
    )


def build_lunar_calendar_post(when: datetime | None = None) -> tuple[str, str]:
    """
    Готовый пост 20:00 — лунный посевной календарь (без LLM).
    """
    when = when or datetime.now(_MSK)
    date_h = f"{when.day} {_MONTHS_RU[when.month - 1]}"
    topic = f"[Лунный календарь] · {date_h}"

    lines = [f"🌙 <b>Лунный календарь · {date_h}</b>", ""]

    explicit = _explicit_day_entry(when)
    if explicit:
        body = _polish_lunar_body(explicit.get("text") or "")
        if body:
            lines.append(body)
        else:
            lines.append(_fallback_lunar_body(when))
    else:
        hit = _pick_best_kizima_chunk(when)
        if hit:
            _src, piece = hit
            polished = _polish_lunar_body(piece)
            lines.append(polished or _fallback_lunar_body(when))
        else:
            lines.append(_fallback_lunar_body(when))

    lines.extend([
        "",
        "Практика дня: одно действие по луне — посев, посадка или уход. Без перегруза грядки.",
        "",
        "#сад #огород #луна #средняяполоса",
    ])
    return topic, "\n".join(lines)


async def resolve_garden_slot(
    slot_value, *, resolve_topic_fn
) -> tuple[str, str | None, str | None, dict | None]:
    """(topic, prebuilt_text, image_path, rubric_seed)."""
    special = is_special_slot(slot_value)
    if special in ("bot_promo", "garden_promo", "[SPECIAL:bot_promo]"):
        topic, text = build_bot_promo_post()
        return topic, text, None, None
    if special in ("kizima_lunar", "lunar_calendar", "[SPECIAL:kizima_lunar]"):
        topic, text = build_lunar_calendar_post()
        return topic, text, None, {"_kind": "garden_lunar"}
    if special in ("garden_curated", "stepanych", "[SPECIAL:garden_curated]"):
        import garden_curated as gc

        return gc.build_garden_curated_post()

    topic = await resolve_topic_fn("garden", slot_value)
    if "[лунный календарь]" in (topic or "").lower():
        t2, text = build_lunar_calendar_post()
        return t2, text, None, {"_kind": "garden_lunar"}
    return topic, None, None, None
