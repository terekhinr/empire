"""Скаут свежих заголовков и поводов для постов.

Источники — публичные RSS-ленты. Результат сохраняется в
data/current_trends.json и подмешивается в prompt LLM как
"живой контекст". Безопасно работает офлайн: если ничего
не удалось вытащить, секции остаются пустыми.

Формат файла:
{
  "updated_at": "...",
  "financial_news": [...],
  "politics_news": [...],
  "topics": {
    "gdepar":  ["заголовок", ...],
    "garden":  ["заголовок", ...],
    "lenin":   ["заголовок", ...]
  }
}
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime

import feedparser
import pytz

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TRENDS_FILE = "data/current_trends.json"
THREE_DAYS_SEC = 3 * 24 * 60 * 60

# ─────────────────────────────────────────────────────────────
# Источники
# ─────────────────────────────────────────────────────────────

FINANCE_FEEDS = [
    "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
    "https://smart-lab.ru/blog/my/rss/",
]
GENERAL_FEEDS = [
    "https://lenta.ru/rss/news",
    "https://www.kommersant.ru/RSS/news.xml",
]
# Общелайфстайл — добавляем дополнительные ленты, где чаще проскакивает
# огород/сад/дача/здоровье. По одной ссылке от каждого крупного агрегатора
# уже даёт достаточный сигнал без зоопарка форумов без RSS.
LIFESTYLE_FEEDS = [
    "https://lenta.ru/rss/news",
    "https://www.kommersant.ru/RSS/news.xml",
    "https://tass.ru/rss/v2.xml",
]

# ─────────────────────────────────────────────────────────────
# Фильтры по ключевым словам и сезону
# ─────────────────────────────────────────────────────────────

FINANCE_KW = [
    "дивиденд", "зпиф", "купон", "ставка", "инфляц", "gldrub",
    "золото", "недвижимост", "цб ", " цб,", "акци", "налог",
    "рубль", "доллар", "юан", "юань", "ипотек",
]

# NB: фильтр идёт регулярками, поэтому даём word-boundary вручную:
# подстрока с пробелом/началом строки, чтобы «бан» не матчилось в «банкир».
GDEPAR_KW = [
    r"\bбан[яеьюий]",
    r"\bпарил",
    r"\bвеник",
    r"\bсаун",
    r"\bхама?м",
    r"\bкупел",
    r"\bзакалив",
    r"\bпар[ ,.;:!?]",
    r"\bпарен",
]

# Базовая «огородная» лексика + сезонные термины (всё через границу слова).
GARDEN_KW_BASE = [
    r"\bдач[аеуи]",
    r"\bогород",
    r"\bсад[ауеыо]",
    r"\bтеплиц",
    r"\bрассад",
    r"\bурожай",
    r"\bгрядк",
    r"\bплодов",
    r"\bягод",
    r"\bхвой",
    r"\bсоток",
    r"\bудобрен",
    r"\bгумус",
    r"\bкомпост",
]
GARDEN_SEASON_KW = {
    1:  [r"\bпосев", r"\bсемен", r"\bобрезк"],
    2:  [r"\bрассад", r"\bсемен", r"\bобрезк"],
    3:  [r"\bрассад", r"\bобрезк", r"\bпобелк"],
    4:  [r"\bрассад", r"\bпосадк", r"\bтеплиц"],
    5:  [r"\bрассад", r"\bпосадк", r"\bзаморозк", r"\bтеплиц"],
    6:  [r"\bприщипк", r"\bпасынков", r"\bтл[яеи]\b", r"\bвредител", r"\bполив"],
    7:  [r"\bполив", r"\bпасынков", r"\bурожай", r"\bфитофтор"],
    8:  [r"\bурожай", r"\bконсерв", r"\bсбор"],
    9:  [r"\bурожай", r"\bсбор", r"\bзаготовк"],
    10: [r"\bзаготовк", r"\bобрезк", r"\bукрыв"],
    11: [r"\bукрыв", r"\bобрезк", r"\bснегозадержан"],
    12: [r"\bпосев", r"\bобрезк", r"\bснегозадержан"],
}

# Для Ленина — поводы для марксистского анализа: «годовщина», «столетие»,
# крупные политэкономические сюжеты. Намеренно избегаем войны/трагедий.
LENIN_KW = [
    r"\bстолет", r"\bгодовщин", r"\bюбилей",
    r"\b100\s*лет", r"\b150\s*лет", r"\b200\s*лет",
    r"\bзабастовк", r"\bпрофсоюз", r"\bклассов",
    r"\bкапитал", r"\bмонопол", r"\bнационализ",
    r"\bприватиз", r"\bинфляци", r"\bтрудящ",
]

# Стоп-слова — никогда не превращаем такие заголовки в темы для канала.
HARD_STOP = [
    r"\bтеракт", r"\bпогибли", r"\bтрагед",
    r"\bкатастроф", r"\bпожар", r"\bсбит",
    r"\bудар\s+по", r"\bразбил",
    r"\bпедофил", r"\bпохорон",
]


# ─────────────────────────────────────────────────────────────
# Парсинг ленты
# ─────────────────────────────────────────────────────────────

def _entries_recent(url: str, max_entries: int = 40) -> list[tuple[str, str]]:
    """Возвращает [(title, summary)] для записей за последние 3 дня."""
    out: list[tuple[str, str]] = []
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        logger.warning(f"[scout] parse error {url}: {e}")
        return out
    now = time.time()
    for entry in feed.entries[:max_entries]:
        title = (entry.get("title") or "").strip()
        if not title:
            continue
        summary = (entry.get("summary") or "").strip()
        # Дата
        published = now
        for attr in ("published_parsed", "updated_parsed"):
            t = entry.get(attr)
            if t:
                try:
                    published = time.mktime(t)
                    break
                except Exception:
                    pass
        if (now - published) > THREE_DAYS_SEC:
            continue
        out.append((title, summary))
    return out


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    out: list[re.Pattern] = []
    for p in patterns:
        try:
            out.append(re.compile(p, re.IGNORECASE | re.UNICODE))
        except re.error as e:
            logger.warning(f"[scout] bad pattern {p!r}: {e}")
    return out


_HARD_STOP_PATTERNS = _compile_patterns(HARD_STOP)


def _match_any(text: str, compiled: list[re.Pattern]) -> bool:
    return any(p.search(text) for p in compiled)


def _is_hard_stop(text: str) -> bool:
    return _match_any(text, _HARD_STOP_PATTERNS)


def _collect(urls: list[str], keywords: list[str], limit: int = 10, allow_any: bool = False) -> list[str]:
    """Собрать с лент заголовки, чьи title/summary матчатся по keywords.
    Если allow_any=True — отдаём все, отсеивая только HARD_STOP (для общей политики)."""
    compiled = _compile_patterns(keywords) if not allow_any else []
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        for title, summary in _entries_recent(url):
            blob = f"{title}\n{summary}"
            if _is_hard_stop(blob):
                continue
            if not allow_any and not _match_any(blob, compiled):
                continue
            key = re.sub(r"\s+", " ", title.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            out.append(f"• {title}")
            if len(out) >= limit:
                return out
    return out


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def _atomic_write_json(path: str, data: dict) -> None:
    """Запись JSON через tmp+replace — читатели не ловят половинчатый файл."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main() -> None:
    logger.info("🕵️‍♂️ Скаут: сбор поводов за 3 дня (финансы / общество / темы по персонам).")
    os.makedirs("data", exist_ok=True)
    month = datetime.now(pytz.timezone("Europe/Moscow")).month

    # FINANCE_KW тут «упрощённые», переоформим как regex по тому же шаблону.
    finance_news = _collect(FINANCE_FEEDS, [rf"\b{kw}" for kw in FINANCE_KW], limit=10)
    politics_news = _collect(GENERAL_FEEDS, [], limit=10, allow_any=True)

    gdepar_topics = _collect(LIFESTYLE_FEEDS, GDEPAR_KW, limit=8)
    garden_kw = GARDEN_KW_BASE + GARDEN_SEASON_KW.get(month, [])
    garden_topics = _collect(LIFESTYLE_FEEDS, garden_kw, limit=8)
    lenin_topics = _collect(GENERAL_FEEDS, LENIN_KW, limit=8)

    report = {
        "updated_at": datetime.now(pytz.timezone("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S"),
        "financial_news": finance_news,
        "politics_news": politics_news,
        "topics": {
            "gdepar": gdepar_topics,
            "garden": garden_topics,
            "lenin": lenin_topics,
        },
    }
    _atomic_write_json(TRENDS_FILE, report)

    logger.info(
        "✅ Скаут: финансы=%d, политика=%d, gdepar=%d, garden=%d, lenin=%d",
        len(finance_news), len(politics_news),
        len(gdepar_topics), len(garden_topics), len(lenin_topics),
    )


if __name__ == "__main__":
    main()
