"""Сценарии Shorts без рендера (ТЗ §4.5)."""

from __future__ import annotations

import json
import logging
import os
import random
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("empire.script_factory")

HOOKS = {
    "garden": "Три ошибки на грядке, которые съедают урожай",
    "gdepar": "Что проверить в бане за 30 секунд до парения",
    "stern": "Одно упражнение для спины без зала",
    "lenin": "Почему этот тезис важен сегодня",
    "pension": "Один шаг к пассивному доходу без паники",
}


async def generate_shorts_scripts(
    session: AsyncSession,
    *,
    personas: list[str] | None = None,
    per_persona: int = 2,
) -> dict[str, int]:
    from main import NewsItem, ShortsScript

    targets = personas or list(HOOKS.keys())
    stats = {"inserted": 0}
    for persona in targets:
        news = (
            await session.execute(
                select(NewsItem)
                .order_by(desc(NewsItem.fetched_at))
                .limit(5)
            )
        ).scalars().all()
        trend = news[0].title[:80] if news else "тренд недели"
        for _ in range(per_persona):
            hook = HOOKS.get(persona, "Смотри до конца")
            bullets = [
                f"Пункт 1: связь с «{trend[:40]}»",
                "Пункт 2: практический совет за 5 секунд",
                "Пункт 3: типичная ошибка зрителя",
            ]
            session.add(
                ShortsScript(
                    persona_key=persona,
                    title=f"{persona}: Short {datetime.now(timezone.utc).strftime('%m%d')}",
                    hook=hook,
                    bullets_json=json.dumps(bullets, ensure_ascii=False),
                    cta=f"Подпишись — ссылка в описании (deeplink {persona})",
                    duration_sec=random.choice([15, 20, 25]),
                    broll_json=json.dumps(
                        ["крупный план рук", "текст на экране", "финальный CTA"],
                        ensure_ascii=False,
                    ),
                    trend_ref=trend,
                    status="ready",
                )
            )
            stats["inserted"] += 1
    await session.commit()
    return stats


def script_to_markdown(row: dict) -> str:
    bullets = json.loads(row.get("bullets_json") or "[]")
    broll = json.loads(row.get("broll_json") or "[]")
    lines = [
        f"# {row.get('title', 'Short')}",
        f"**Персона:** {row.get('persona_key')}",
        f"**Хук (0–3 с):** {row.get('hook')}",
        "",
        "## Три пункта",
    ]
    for i, b in enumerate(bullets, 1):
        lines.append(f"{i}. {b}")
    lines.extend(
        [
            "",
            f"**CTA:** {row.get('cta')}",
            f"**Длительность:** ~{row.get('duration_sec')} с",
            "",
            "## B-roll",
        ]
    )
    for b in broll:
        lines.append(f"- {b}")
    if row.get("trend_ref"):
        lines.extend(["", f"_Тренд:_ {row['trend_ref']}"])
    return "\n".join(lines)
