"""Сквозная аналитика — схема analytics.db (ТЗ FINAL §4.4, фаза 3)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

ANALYTICS_DB_PATH = Path(os.getenv("EMPIRE_ANALYTICS_DB", "analytics.db"))


def init_analytics_db(path: Path | None = None) -> None:
    p = path or ANALYTICS_DB_PATH
    conn = sqlite3.connect(p)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL UNIQUE,
            persona_key TEXT,
            label TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            source_id TEXT,
            persona_key TEXT,
            payload_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
        CREATE TABLE IF NOT EXISTS daily_subs (
            day TEXT NOT NULL,
            channel TEXT NOT NULL,
            persona_key TEXT,
            subscribers INTEGER,
            PRIMARY KEY (day, channel, persona_key)
        );
        CREATE TABLE IF NOT EXISTS daily_revenue (
            day TEXT NOT NULL,
            source_id TEXT,
            amount_rub REAL,
            PRIMARY KEY (day, source_id)
        );
        CREATE TABLE IF NOT EXISTS agg_daily (
            day TEXT PRIMARY KEY,
            metrics_json TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def log_event(event_type: str, *, source_id: str | None = None, persona_key: str | None = None, payload: dict | None = None) -> None:
    import json

    init_analytics_db()
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.execute(
        "INSERT INTO events (event_type, source_id, persona_key, payload_json) VALUES (?,?,?,?)",
        (
            event_type,
            source_id,
            persona_key,
            json.dumps(payload or {}, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()
