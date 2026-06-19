"""News-парсер RSS → таблица news (ТЗ FINAL §4.3.1)."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scout import FINANCE_FEEDS, GENERAL_FEEDS, LIFESTYLE_FEEDS

logger = logging.getLogger("empire.news_rss")

FEED_MAP: list[tuple[str, str]] = (
    [(u, "finance") for u in FINANCE_FEEDS]
    + [(u, "politics") for u in GENERAL_FEEDS]
    + [(u, "lifestyle") for u in LIFESTYLE_FEEDS]
)


def _url_hash(url: str) -> str:
    return hashlib.sha256((url or "").strip().encode("utf-8")).hexdigest()[:40]


def _parse_entry(entry: Any) -> tuple[str, str, datetime | None]:
    title = (getattr(entry, "title", None) or "").strip()
    link = (getattr(entry, "link", None) or "").strip()
    published = None
    if getattr(entry, "published_parsed", None):
        try:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            published = None
    return title, link, published


async def ingest_rss_feeds(session: AsyncSession, *, limit_per_feed: int = 15) -> dict[str, int]:
    from main import NewsItem

    stats = {"inserted": 0, "skipped": 0, "feeds": 0}
    seen_feeds: set[str] = set()
    for feed_url, category in FEED_MAP:
        if feed_url in seen_feeds:
            continue
        seen_feeds.add(feed_url)
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            logger.warning("feed_fail %s %s", feed_url[:40], type(exc).__name__)
            continue
        stats["feeds"] += 1
        entries = getattr(parsed, "entries", [])[:limit_per_feed]
        for entry in entries:
            title, link, published = _parse_entry(entry)
            if not title or not link:
                stats["skipped"] += 1
                continue
            uh = _url_hash(link)
            exists = (
                await session.execute(select(NewsItem).where(NewsItem.url_hash == uh))
            ).scalar_one_or_none()
            if exists:
                stats["skipped"] += 1
                continue
            session.add(
                NewsItem(
                    url_hash=uh,
                    url=link,
                    title=title[:500],
                    source_feed=feed_url[:200],
                    category=category,
                    published_at=published,
                )
            )
            stats["inserted"] += 1
    await session.commit()
    return stats
