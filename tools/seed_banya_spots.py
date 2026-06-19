#!/usr/bin/env python3
"""Заливает в empire.db список общественных бань из data/gdepar_spots_seed.json.

Автономный скрипт: не импортирует main.py (а значит не тянет HF-модель).
Работает через прямой sqlite3, INSERT/UPDATE по slug, идемпотентно.
Все записи попадают со status='draft'. На сайт показываем только status='published'
(меняется через Telegram-команду /banya pub <slug-или-id>).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEED_FILE = ROOT / "data" / "gdepar_spots_seed.json"
DB_PATH = ROOT / "empire.db"


DDL = """
CREATE TABLE IF NOT EXISTS banya_spots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE,
    title TEXT,
    city TEXT,
    address TEXT,
    lat TEXT,
    lon TEXT,
    heating TEXT,
    kind TEXT,
    site_url TEXT,
    phone TEXT,
    yandex_url TEXT,
    twogis_url TEXT,
    cover_url TEXT,
    description TEXT,
    clips_json TEXT,
    tags_json TEXT,
    visited INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft',
    rating_avg TEXT,
    reviews_total INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_banya_spots_city   ON banya_spots(city);
CREATE INDEX IF NOT EXISTS idx_banya_spots_status ON banya_spots(status);

CREATE TABLE IF NOT EXISTS banya_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spot_id INTEGER,
    source TEXT,
    source_id TEXT,
    author TEXT,
    rating INTEGER,
    text TEXT,
    url TEXT,
    published_at TEXT,
    fetched_at TEXT,
    status TEXT DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS idx_banya_reviews_spot   ON banya_reviews(spot_id);
CREATE INDEX IF NOT EXISTS idx_banya_reviews_source ON banya_reviews(source);
CREATE INDEX IF NOT EXISTS idx_banya_reviews_status ON banya_reviews(status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_banya_reviews_src_id
    ON banya_reviews(source, source_id)
    WHERE source_id IS NOT NULL;
"""


def _ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(DDL)
    con.commit()


def _tags_to_json(tags) -> str | None:
    if not tags:
        return None
    return json.dumps(tags, ensure_ascii=False)


def seed() -> None:
    if not SEED_FILE.exists():
        print(f"SEED: нет файла {SEED_FILE}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    spots = data.get("spots", [])
    if not spots:
        print("SEED: список пуст")
        return

    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    try:
        _ensure_schema(con)
        cur = con.cursor()
        now = datetime.utcnow().isoformat(timespec="seconds")
        created = updated = 0
        for s in spots:
            slug = (s.get("slug") or "").strip()
            if not slug:
                continue
            row = cur.execute(
                "SELECT id FROM banya_spots WHERE slug = ?", (slug,)
            ).fetchone()
            fields = dict(
                slug=slug,
                title=s.get("title"),
                city=s.get("city"),
                address=s.get("address"),
                lat=str(s["lat"]) if s.get("lat") is not None else None,
                lon=str(s["lon"]) if s.get("lon") is not None else None,
                heating=s.get("heating") or "unknown",
                kind=s.get("kind") or "public",
                site_url=s.get("site_url"),
                phone=s.get("phone"),
                yandex_url=s.get("yandex_url"),
                twogis_url=s.get("twogis_url"),
                cover_url=s.get("cover_url"),
                description=s.get("description"),
                tags_json=_tags_to_json(s.get("tags")),
                visited=1 if s.get("visited") else 0,
            )
            if row:
                set_clauses = ", ".join(f"{k} = ?" for k in fields if k != "slug")
                cur.execute(
                    f"UPDATE banya_spots SET {set_clauses}, updated_at = ? WHERE slug = ?",
                    [v for k, v in fields.items() if k != "slug"] + [now, slug],
                )
                updated += 1
            else:
                cols = list(fields.keys()) + ["status", "created_at", "updated_at"]
                vals = list(fields.values()) + ["draft", now, now]
                placeholders = ", ".join("?" * len(cols))
                cur.execute(
                    f"INSERT INTO banya_spots ({', '.join(cols)}) VALUES ({placeholders})",
                    vals,
                )
                created += 1
        con.commit()
    finally:
        con.close()

    print(f"SEED: добавлено {created}, обновлено {updated}, всего в seed {len(spots)}")


if __name__ == "__main__":
    os.chdir(ROOT)
    seed()
