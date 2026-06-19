"""Сводные метрики Pension: JSON на диск + daily_subs в analytics.db."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from analytics_db import init_analytics_db, log_event

BASE_DIR = Path(__file__).resolve().parent
WEEKLY_JSON = BASE_DIR / "data" / "pension_weekly_metrics.json"
WAITLIST_JSON = BASE_DIR / "data" / "pension_waitlist.json"


def _load_json_list(path: Path) -> list:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_json_list(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_weekly_metrics() -> list[dict]:
    return _load_json_list(WEEKLY_JSON)


def save_weekly_row(row: dict) -> None:
    """Добавить или обновить строку по полю week (ISO date понедельника или YYYY-Www)."""
    week = (row.get("week") or "").strip()
    if not week:
        week = date.today().isoformat()
    row = {**row, "week": week}
    rows = load_weekly_metrics()
    rows = [r for r in rows if (r.get("week") or "") != week]
    rows.append(row)
    rows.sort(key=lambda r: r.get("week") or "")
    _save_json_list(WEEKLY_JSON, rows)
    init_analytics_db()
    log_event("pension_weekly_metrics_saved", persona_key="pension", payload={"week": week})


def append_waitlist_email(email: str, *, source: str = "site") -> bool:
    email = (email or "").strip().lower()
    if not email or "@" not in email or len(email) > 254:
        return False
    rows = _load_json_list(WAITLIST_JSON)
    if any(r.get("email") == email for r in rows):
        return True
    rows.append(
        {
            "email": email,
            "source": source,
            "created_at": date.today().isoformat(),
        }
    )
    _save_json_list(WAITLIST_JSON, rows)
    log_event("pension_waitlist_signup", persona_key="pension", payload={"source": source})
    return True


def waitlist_count() -> int:
    return len(_load_json_list(WAITLIST_JSON))


def record_daily_subs(
    *,
    tg: int | None = None,
    vk: int | None = None,
    dzen: int | None = None,
    youtube: int | None = None,
    day: str | None = None,
) -> None:
    import sqlite3

    from analytics_db import ANALYTICS_DB_PATH

    init_analytics_db()
    d = day or date.today().isoformat()
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    for channel, val in (("tg", tg), ("vk", vk), ("dzen", dzen), ("youtube", youtube)):
        if val is None:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO daily_subs (day, channel, persona_key, subscribers) "
            "VALUES (?,?,?,?)",
            (d, channel, "pension", int(val)),
        )
    conn.commit()
    conn.close()
    log_event("pension_daily_subs", persona_key="pension", payload={"day": d})


def latest_daily_subs() -> dict[str, int]:
    import sqlite3

    from analytics_db import ANALYTICS_DB_PATH

    if not ANALYTICS_DB_PATH.is_file():
        return {}
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    rows = conn.execute(
        "SELECT channel, subscribers FROM daily_subs "
        "WHERE persona_key='pension' AND day = ("
        "  SELECT MAX(day) FROM daily_subs WHERE persona_key='pension'"
        ") ORDER BY channel"
    ).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows if r[1] is not None}
