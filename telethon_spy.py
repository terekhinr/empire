"""Telethon-Spy: сигналы только для gdepar/stern. Dry-run — только при SPY_ALLOW_DRY_RUN=1."""

from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

import spy_config

logger = logging.getLogger("empire.telethon_spy")
CONFIG_PATH = Path(__file__).resolve().parent / "data" / "spy_competitors.json"
ANOMALY_ER_THRESHOLD = float(__import__("os").getenv("SPY_ANOMALY_ER_THRESHOLD", "0.08"))


def _load_competitors() -> dict[str, list[str]]:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return {
            k: [h for h in v if isinstance(h, str) and h.strip()]
            for k, v in raw.items()
            if isinstance(v, list) and spy_config.persona_uses_spy_content(k)
        }
    except (json.JSONDecodeError, OSError):
        return {}


async def run_spy_dry_run(session: AsyncSession, *, max_per_persona: int = 8) -> dict[str, int]:
    """Заглушка из news — только gdepar/stern и только если SPY_ALLOW_DRY_RUN=1."""
    from main import NewsItem, SpySignal

    if not spy_config.spy_dry_run_allowed():
        logger.info("spy dry-run disabled (set SPY_ALLOW_DRY_RUN=1 for dev only)")
        return {"inserted": 0, "skipped": 0, "disabled": "dry_run_off"}

    if spy_config.spy_live_enabled():
        logger.info("telethon session ready — use run_spy_collect / run_spy_live")
        return {"inserted": 0, "skipped": 0, "disabled": "use_run_spy_collect"}

    competitors = _load_competitors()
    if not competitors:
        return {"inserted": 0, "skipped": 0, "disabled": "no_competitors"}

    since = datetime.now(timezone.utc) - timedelta(days=7)
    stats: dict[str, int] = {"inserted": 0, "skipped": 0}

    for persona, handles in competitors.items():
        if not handles:
            continue
        stmt = (
            select(NewsItem)
            .where(NewsItem.fetched_at >= since.replace(tzinfo=None))
            .order_by(desc(NewsItem.fetched_at))
            .limit(30)
        )
        news_rows = (await session.execute(stmt)).scalars().all()
        count = 0
        for item in news_rows:
            if count >= max_per_persona:
                break
            er = round(random.uniform(0.03, 0.22), 4)
            if er < ANOMALY_ER_THRESHOLD:
                stats["skipped"] += 1
                continue
            competitor = random.choice(handles)
            post_ref = item.url or item.title
            dup = (
                await session.execute(
                    select(SpySignal).where(
                        SpySignal.persona_key == persona,
                        SpySignal.post_ref == post_ref,
                    )
                )
            ).scalar_one_or_none()
            if dup:
                stats["skipped"] += 1
                continue
            session.add(
                SpySignal(
                    persona_key=persona,
                    competitor=competitor,
                    post_url=item.url,
                    post_text=item.title,
                    post_ref=post_ref[:500],
                    er_proxy=str(er),
                    anomaly_score=str(round(er / ANOMALY_ER_THRESHOLD, 2)),
                    status="new",
                    source="dry_run_news",
                )
            )
            stats["inserted"] += 1
            count += 1
    await session.commit()
    return stats


def _message_engagement(msg, participants: int) -> tuple[float, int]:
    """ER proxy: views/subscribers (реакции — запасной сигнал)."""
    views = int(msg.views or 0)
    reactions = 0
    if getattr(msg, "reactions", None) and getattr(msg.reactions, "results", None):
        reactions = sum(int(getattr(r, "count", 0) or 0) for r in msg.reactions.results)
    if participants > 100:
        er = views / participants
    elif views > 500:
        er = min(0.25, views / 5000.0)
    else:
        er = 0.0
    if reactions >= 15 and er < ANOMALY_ER_THRESHOLD:
        er = max(er, ANOMALY_ER_THRESHOLD + 0.01)
    return er, views


async def run_spy_live(
    session: AsyncSession,
    *,
    max_messages_per_channel: int = 30,
    lookback_days: int = 7,
) -> dict[str, int | str]:
    """Чтение публичных TG-каналов конкурентов через Telethon → spy_signals."""
    from main import SpySignal

    if not spy_config.spy_live_enabled():
        return {"inserted": 0, "skipped": 0, "disabled": "no_session"}

    import os

    from telethon import TelegramClient
    from telethon.tl.functions.channels import GetFullChannelRequest
    from telethon.tl.types import Channel

    competitors = _load_competitors()
    if not competitors:
        return {"inserted": 0, "skipped": 0, "disabled": "no_competitors"}

    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    stats: dict[str, int | str] = {"inserted": 0, "skipped": 0, "channels": 0, "errors": 0}

    api_id = int(os.getenv("TELETHON_API_ID", "0"))
    api_hash = os.getenv("TELETHON_API_HASH", "").strip()
    session_path = str(spy_config.telethon_session_path())

    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        logger.warning("spy live: Telethon session not authorized")
        return {**stats, "disabled": "not_authorized"}

    try:
        for persona, handles in competitors.items():
            for handle in handles:
                h = handle.strip()
                if not h:
                    continue
                try:
                    stats["channels"] = int(stats["channels"]) + 1
                    entity = await client.get_entity(h)
                    participants = int(getattr(entity, "participants_count", 0) or 0)
                    if isinstance(entity, Channel):
                        try:
                            full = await client(GetFullChannelRequest(entity))
                            participants = int(full.full_chat.participants_count or participants)
                        except Exception:
                            pass

                    messages = await client.get_messages(entity, limit=max_messages_per_channel)
                    for msg in messages:
                        if not msg or not msg.date:
                            continue
                        msg_dt = msg.date
                        if msg_dt.tzinfo is None:
                            msg_dt = msg_dt.replace(tzinfo=timezone.utc)
                        if msg_dt < since:
                            continue
                        text = (getattr(msg, "message", None) or getattr(msg, "text", None) or "").strip()
                        if len(text) < 40:
                            stats["skipped"] = int(stats["skipped"]) + 1
                            continue

                        er, _views = _message_engagement(msg, participants)
                        if er < ANOMALY_ER_THRESHOLD:
                            stats["skipped"] = int(stats["skipped"]) + 1
                            continue

                        username = h.lstrip("@")
                        post_url = f"https://t.me/{username}/{msg.id}"
                        post_ref = f"{h}:{msg.id}"

                        dup = (
                            await session.execute(
                                select(SpySignal).where(SpySignal.post_ref == post_ref)
                            )
                        ).scalar_one_or_none()
                        if dup:
                            stats["skipped"] = int(stats["skipped"]) + 1
                            continue

                        session.add(
                            SpySignal(
                                persona_key=persona,
                                competitor=h,
                                post_url=post_url,
                                post_text=text[:2000],
                                post_ref=post_ref[:500],
                                er_proxy=str(round(er, 4)),
                                anomaly_score=str(round(er / ANOMALY_ER_THRESHOLD, 2)),
                                status="new",
                                source="telethon",
                            )
                        )
                        stats["inserted"] = int(stats["inserted"]) + 1
                except Exception as exc:
                    logger.warning("spy live channel %s: %s", h, exc)
                    stats["errors"] = int(stats["errors"]) + 1
        await session.commit()
    finally:
        await client.disconnect()

    logger.info(
        "spy live: inserted=%s skipped=%s channels=%s errors=%s",
        stats["inserted"],
        stats["skipped"],
        stats["channels"],
        stats["errors"],
    )
    return stats


async def run_spy_collect(session: AsyncSession, **kwargs) -> dict:
    """Live Telethon, иначе dry-run (только при SPY_ALLOW_DRY_RUN=1)."""
    if spy_config.spy_live_enabled():
        return await run_spy_live(session, **kwargs)
    return await run_spy_dry_run(session, **kwargs)
