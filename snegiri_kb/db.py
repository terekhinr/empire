"""SQLite persistence for Snegiri sessions."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "snegiri" / "kb_trainer.db"
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "snegiri" / "uploads"


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                profile_json TEXT NOT NULL DEFAULT '{}',
                state_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                exercise_slug TEXT NOT NULL,
                score REAL NOT NULL,
                result_json TEXT NOT NULL,
                video_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_analyses_session ON analyses(session_id);
            """
        )


def _connect() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_session(profile: dict | None = None, state: dict | None = None) -> dict:
    sid = uuid.uuid4().hex
    now = _utcnow()
    profile = profile or {}
    state = state or {}
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_at, updated_at, profile_json, state_json) VALUES (?, ?, ?, ?, ?)",
            (sid, now, now, json.dumps(profile, ensure_ascii=False), json.dumps(state, ensure_ascii=False)),
        )
    return get_session(sid)


def get_session(session_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "profile": json.loads(row["profile_json"] or "{}"),
        "state": json.loads(row["state_json"] or "{}"),
    }


def update_session(session_id: str, *, profile: dict | None = None, state: dict | None = None) -> dict | None:
    cur = get_session(session_id)
    if not cur:
        return None
    if profile is not None:
        cur["profile"] = {**cur.get("profile", {}), **profile}
    if state is not None:
        cur["state"] = {**cur.get("state", {}), **state}
    now = _utcnow()
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET updated_at = ?, profile_json = ?, state_json = ? WHERE id = ?",
            (
                now,
                json.dumps(cur["profile"], ensure_ascii=False),
                json.dumps(cur["state"], ensure_ascii=False),
                session_id,
            ),
        )
    cur["updatedAt"] = now
    return cur


def save_analysis(
    session_id: str,
    exercise_slug: str,
    score: float,
    result: dict[str, Any],
    video_path: str | None = None,
) -> dict:
    now = _utcnow()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO analyses (session_id, exercise_slug, score, result_json, video_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, exercise_slug, score, json.dumps(result, ensure_ascii=False), video_path, now),
        )
        aid = cur.lastrowid
    return {"id": aid, "sessionId": session_id, "exerciseSlug": exercise_slug, "score": score, "createdAt": now}


def list_analyses(session_id: str, limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, exercise_slug, score, result_json, created_at FROM analyses WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "exerciseSlug": r["exercise_slug"],
                "score": r["score"],
                "result": json.loads(r["result_json"] or "{}"),
                "createdAt": r["created_at"],
            }
        )
    return out
