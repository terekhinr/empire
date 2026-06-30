#!/usr/bin/env python3
"""Схема MVP Gdepar B2B: лиды, профиль бани, SEO (миграция SQLite).

Вызывается из osm_banyas, gdepar_app startup, CLI:
  ./venv/bin/python tools/banya_schema_mvp.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "empire.db"

# Новые колонки banya_spots (идемпотентный ALTER)
BANYA_SPOT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("price_from", "INTEGER"),
    ("price_per_hour", "INTEGER"),
    ("capacity_max", "INTEGER"),
    ("has_pool", "INTEGER DEFAULT 0"),
    ("has_tub", "INTEGER DEFAULT 0"),
    ("own_venik_allowed", "INTEGER"),
    ("bath_style", "TEXT"),
    ("district", "TEXT"),
    ("partner_tier", "TEXT DEFAULT 'free'"),
    ("owner_account_id", "INTEGER"),
    ("map_views", "INTEGER DEFAULT 0"),
    ("cpa_trial_calls_credited", "INTEGER DEFAULT 0"),
    ("cpa_deposit_balance", "INTEGER DEFAULT 0"),
    ("phone_blocked", "INTEGER DEFAULT 0"),
)


def ensure_banya_mvp_schema(con: sqlite3.Connection) -> None:
    """Добавляет колонки и таблицы MVP без потери данных."""
    for col, ddl in BANYA_SPOT_COLUMNS:
        try:
            con.execute(f"ALTER TABLE banya_spots ADD COLUMN {col} {ddl}")
        except sqlite3.OperationalError:
            pass

    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS banya_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spot_id INTEGER NOT NULL,
            lead_type TEXT NOT NULL,
            source TEXT DEFAULT 'site',
            session_id TEXT,
            referrer TEXT,
            payload_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_banya_leads_spot ON banya_leads(spot_id);
        CREATE INDEX IF NOT EXISTS idx_banya_leads_created ON banya_leads(created_at);
        CREATE INDEX IF NOT EXISTS idx_banya_leads_type ON banya_leads(lead_type);

        CREATE TABLE IF NOT EXISTS banya_call_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spot_id INTEGER NOT NULL,
            duration_sec INTEGER NOT NULL,
            external_id TEXT,
            credited INTEGER DEFAULT 0,
            payload_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_banya_call_events_spot ON banya_call_events(spot_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_banya_call_events_ext
            ON banya_call_events(external_id) WHERE external_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS banya_owner_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            phone TEXT,
            company_name TEXT,
            subscription_tier TEXT DEFAULT 'free',
            balance_rub REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS seo_landings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            h1 TEXT,
            body_html TEXT,
            query_tag TEXT,
            district TEXT,
            heating_type TEXT,
            spot_ids_json TEXT,
            ai_generated INTEGER DEFAULT 1,
            status TEXT DEFAULT 'draft',
            published_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_seo_landings_status ON seo_landings(status);
        """
    )
    con.commit()


def main() -> int:
    db = DB_PATH
    if not db.is_file():
        print(f"БД не найдена: {db}")
        return 1
    con = sqlite3.connect(str(db))
    con.execute("PRAGMA journal_mode=WAL")
    ensure_banya_mvp_schema(con)
    con.close()
    print(f"OK: MVP-схема применена к {db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
