"""Пенсия: лента сырых новостей (raw) и подсказки голоса для разборов."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

_ROOT = Path(__file__).resolve().parent
_VOICE_CFG = _ROOT / "data" / "pension_voice_config.json"

MILITARY_KW = (
    "войн",
    "фронт",
    "сво",
    "удар",
    "дрон",
    "арми",
    "нато",
    "санкц",
    "ракет",
    "мобилиз",
    "окоп",
    "бпла",
)


def _load_voice_cfg() -> dict:
    if not _VOICE_CFG.is_file():
        return {}
    return json.loads(_VOICE_CFG.read_text(encoding="utf-8"))


def is_raw_news_slot(slot_value) -> str | None:
    """Возвращает feed-ключ: finance | politics | politics_military."""
    if isinstance(slot_value, dict):
        t = (slot_value.get("type") or "").strip().lower()
        if t == "raw_news":
            return (slot_value.get("feed") or "finance").strip().lower()
    if isinstance(slot_value, str):
        m = re.match(r"\[RAW:(\w+)\]", slot_value.strip(), re.I)
        if m:
            return m.group(1).lower()
        low = slot_value.lower()
        if "финанс" in low:
            return "finance"
        if "полит" in low:
            return "politics_military"
    return None


_VOICE_LABEL_MAP = {
    "антонов": "antonov",
    "марков": "markov",
    "кримсон": "crimson",
    "талеб": "taleb",
}


def voice_prompt_block(selected_labels: list[str] | None = None) -> str:
    cfg = _load_voice_cfg()
    voices = cfg.get("voices", [])
    if not voices:
        return ""
    lines = [
        "\nГОЛОСА ДЛЯ ТОНА (не копируй дословно, только манера):",
        f"• Не больше {cfg.get('max_taleb_mentions_per_post', 1)} отсылки к Талебу за пост.",
    ]
    if selected_labels:
        lines.append("• В этом разборе используй углы: " + ", ".join(selected_labels) + ".")
    else:
        lines.append("• Чередуй авторов: " + ", ".join(cfg.get("rotate_authors", [])) + ".")
    for v in voices:
        if not isinstance(v, dict):
            continue
        lab = v.get("label", "")
        if selected_labels:
            if not any(s.lower() in lab.lower() or lab.lower() in s.lower() for s in selected_labels):
                if lab == "Талеб" and "Талеб" not in selected_labels:
                    continue
        lines.append(
            f"• {lab}: {v.get('tone_hint', '')} "
            f"(канал: {v.get('telegram', '')})"
        )
    if "Марков" in (selected_labels or []) or not selected_labels:
        lines.append("• Марков: прагматичный разбор рисков и сценариев (без штампов).")
    lines.append(
        "• Факты — из новости дня и БАЗЫ ЗНАНИЙ; не имитируй каналы 1:1."
    )
    return "\n".join(lines)


def parse_voices_from_topic(topic_raw: str) -> list[str]:
    m = re.search(r"ГОЛОСА РАЗБОРА[^:]*:\s*([^\n]+)", topic_raw or "", re.I)
    if not m:
        return []
    return [x.strip() for x in m.group(1).split(",") if x.strip()]


async def fetch_headlines(
    session: AsyncSession,
    *,
    feed: str,
    limit: int = 8,
    hours: int = 72,
) -> list[dict]:
    from main import NewsItem

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(NewsItem)
        .where(NewsItem.fetched_at >= since)
        .order_by(desc(NewsItem.fetched_at))
        .limit(limit * 4)
    )
    rows = (await session.execute(stmt)).scalars().all()
    out: list[dict] = []
    for row in rows:
        title = (row.title or "").strip()
        if not title:
            continue
        cat = (row.category or "").lower()
        low = title.lower()
        if feed == "finance":
            if cat not in ("finance",) and not any(
                k in low for k in ("рубл", "акци", "банк", "ставк", "инфляц", "нефт", "бирж")
            ):
                continue
        elif feed in ("politics", "politics_military"):
            is_mil = any(k in low for k in MILITARY_KW)
            if cat == "finance" and not is_mil:
                continue
            if feed == "politics_military" and cat == "lifestyle":
                continue
        else:
            continue
        out.append({"title": title, "url": row.url, "category": cat})
        if len(out) >= limit:
            break
    return out


def _format_digest(feed: str, items: list[dict]) -> str:
    titles = {
        "finance": "📰 Финансы · свежие заголовки",
        "politics": "📰 Политика · свежие заголовки",
        "politics_military": "📰 Политика и военное · свежие заголовки",
    }
    head = titles.get(feed, "📰 Новости · лента")
    if not items:
        return (
            f"<b>{head}</b>\n\n"
            "За последние 3 дня в ленте RSS пока пусто — обновите ingest или выберите разбор вручную.\n\n"
            "#новости #финансы #экономика"
        )
    lines = [f"<b>{head}</b>\n"]
    for it in items:
        t = it["title"].replace("<", "").replace(">", "")
        url = it.get("url") or ""
        if url:
            lines.append(f"• <a href=\"{url}\">{t}</a>")
        else:
            lines.append(f"• {t}")
    lines.append(
        "\n<i>Разбор по одной новости — вручную из дашборда (тема с префиксом [ANALYSIS]).</i>"
    )
    tags = "#новости #финансы #экономика" if feed == "finance" else "#новости #политика #геополитика"
    lines.append(f"\n{tags}")
    return "\n".join(lines)


async def build_raw_news_prebuilt(
    session: AsyncSession,
    feed: str,
) -> tuple[str, str]:
    items = await fetch_headlines(session, feed=feed, limit=8)
    topic = f"[RAW:{feed}] Лента заголовков"
    body = _format_digest(feed, items)
    return topic, body
