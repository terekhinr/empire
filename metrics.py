"""Снимки метрик → analytics.db (ТЗ §4.4, фаза 3)."""

from __future__ import annotations

import json
import sqlite3
from datetime import date

from analytics_db import ANALYTICS_DB_PATH, init_analytics_db, log_event

PLATFORM_TARGETS_FLAT = {
    "garden": "-1002008085075",
    "lenin": "-1002136411597",
    "stern": "-1002024827297",
    "gdepar": "-1003960332245",
}


def snapshot_daily_subs(*, subscribers: int | None = None) -> None:
    """Заглушка снапшота: пишет placeholder, пока нет TG getChatMemberCount."""
    init_analytics_db()
    day = date.today().isoformat()
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    for persona, _chat in PLATFORM_TARGETS_FLAT.items():
        conn.execute(
            "INSERT OR REPLACE INTO daily_subs (day, channel, persona_key, subscribers) "
            "VALUES (?,?,?,?)",
            (day, "tg", persona, subscribers),
        )
    conn.commit()
    conn.close()
    log_event("daily_snapshot", payload={"day": day, "mode": "placeholder"})


def weekly_events_summary(days: int = 7) -> dict:
    init_analytics_db()
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    rows = conn.execute(
        "SELECT event_type, COUNT(*) FROM events "
        "WHERE created_at >= datetime('now', ?) GROUP BY event_type",
        (f"-{days} days",),
    ).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def build_ai_insights_stub() -> dict:
    """Каркас AI Insights без вызова Claude (нет PII)."""
    from pii_validator import validate_payload_for_llm

    summary = weekly_events_summary()
    hypotheses = [
        "Усилить CTA с deeplink в постах garden — мало bot_started.",
        "Проверить ER-аномалии gdepar: топ-3 сигнала → черновики.",
        "Shorts stern: 2 ролика/нед по готовым сценариям из дашборда.",
    ]
    payload = {"events_7d": summary, "hypotheses": hypotheses}
    return validate_payload_for_llm(payload)


def save_weekly_insights_file() -> str:
    """Сохраняет JSON-отчёт в data/insights/ для дашборда."""
    import json
    from datetime import date
    from pathlib import Path

    out_dir = Path(__file__).resolve().parent / "data" / "insights"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"insights_{date.today().isoformat()}.json"
    data = build_ai_insights_stub()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)
