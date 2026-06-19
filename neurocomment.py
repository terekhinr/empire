"""Нейрокомментинг — только dry-run (ТЗ §4.3.3)."""

from __future__ import annotations

import json
import logging
import os
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from analytics_db import log_event

logger = logging.getLogger("empire.neurocomment")

MAX_PER_HOUR = int(os.getenv("NEUROCOMMENT_MAX_PER_HOUR", "5"))
BLOCKED_WORDS = ("война", "убий", "террор", "наркот")


def _blocked(text: str) -> str | None:
    low = (text or "").lower()
    for w in BLOCKED_WORDS:
        if w in low:
            return w
    return None


async def run_neurocomment_dry_run(session: AsyncSession) -> dict[str, int]:
    from main import NeurocommentPlan, SpySignal

    hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = (
        await session.execute(
            select(func.count())
            .select_from(NeurocommentPlan)
            .where(NeurocommentPlan.created_at >= hour_ago.replace(tzinfo=None))
        )
    ).scalar() or 0
    if recent >= MAX_PER_HOUR:
        return {"inserted": 0, "skipped": 0, "limit": recent}

    signals = (
        await session.execute(
            select(SpySignal)
            .where(SpySignal.status == "new")
            .order_by(desc(SpySignal.anomaly_score))
            .limit(MAX_PER_HOUR)
        )
    ).scalars().all()

    stats = {"inserted": 0, "skipped": 0}
    templates = [
        "Интересный ракурс — спасибо за цифры.",
        "Согласен с выводом, добавил бы только про риски.",
        "Полезно, сохранил в закладки.",
    ]
    for sig in signals:
        planned = random.choice(templates)
        block = _blocked(sig.post_text or "")
        status = "blocked" if block else "dry_run"
        reason = f"blocked_word:{block}" if block else "dry_run_no_send"
        session.add(
            NeurocommentPlan(
                persona_key=sig.persona_key,
                channel_ref=sig.competitor,
                post_ref=sig.post_ref or sig.post_url,
                planned_text=planned,
                reason=reason,
                status=status,
            )
        )
        log_event(
            "neurocomment_planned",
            persona_key=sig.persona_key,
            payload={"status": status, "reason": reason, "post_ref": sig.post_ref},
        )
        stats["inserted"] += 1
    await session.commit()
    return stats
