"""Источники трафика: source_id и deeplink (ТЗ §4.4)."""

from __future__ import annotations

import secrets
import sqlite3
from pathlib import Path

from analytics_db import ANALYTICS_DB_PATH, init_analytics_db

BOT_USERNAME = __import__("os").getenv("EMPIRE_BOT_USERNAME", "neverretire_bot")


def generate_source_id(persona_key: str, label: str = "") -> str:
    slug = (label or persona_key or "src")[:12].replace(" ", "_")
    return f"{slug}_{secrets.token_hex(4)}"


def register_link(source_id: str, persona_key: str, label: str = "") -> None:
    init_analytics_db()
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO links (source_id, persona_key, label) VALUES (?,?,?)",
        (source_id, persona_key, label or None),
    )
    conn.commit()
    conn.close()


def deeplink_tg(source_id: str) -> str:
    user = BOT_USERNAME.lstrip("@")
    return f"https://t.me/{user}?start={source_id}"


def list_links(limit: int = 100) -> list[dict]:
    init_analytics_db()
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT source_id, persona_key, label, created_at FROM links ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
