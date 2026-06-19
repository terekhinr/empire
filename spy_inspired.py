"""Автослот: лучший spy_signal за неделю → тема для генерации (approve обязателен)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("empire.spy_inspired")


import spy_config


async def pick_best_spy_signal(
    session: AsyncSession,
    persona_key: str,
    *,
    days: int = 7,
) -> object | None:
    from main import SpySignal

    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(SpySignal)
        .where(
            SpySignal.persona_key == persona_key,
            SpySignal.created_at >= since.replace(tzinfo=None),
            SpySignal.status.in_(("new", "scheduled")),
        )
        .order_by(desc(SpySignal.anomaly_score), desc(SpySignal.created_at))
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def resolve_spy_inspired_topic(session: AsyncSession, persona_key: str) -> str:
    from spy_to_draft import _topic_from_signal

    if not spy_config.persona_uses_spy_content(persona_key):
        return (
            f"[spy_inspired] Разведка не для {persona_key} — возьми тему из расписания."
        )
    if not spy_config.can_run_spy_pipeline():
        return (
            f"[spy_inspired] Telethon не подключён — свободная тема для {persona_key} "
            "из расписания (без разведки)."
        )

    sig = await pick_best_spy_signal(session, persona_key)
    if not sig:
        return (
            f"[spy_inspired] Свободная тема для {persona_key}: "
            "сигналов разведки за 7 дней нет — возьми свежий угол из расписания."
        )
    sig.status = "scheduled"
    await session.commit()
    base = _topic_from_signal(sig)
    return (
        f"[spy_inspired] {base}\n\n"
        "ЗАДАЧА: переработай мотив взлётного поста конкурента в НОВЫЙ пост нашего канала. "
        "Не копируй текст и не упоминай конкурента по имени. Сохрани тон персоны."
    )
