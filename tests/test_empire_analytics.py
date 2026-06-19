from pathlib import Path

from analytics_db import init_analytics_db, log_event


def test_init_and_log_event(tmp_path, monkeypatch):
    db = tmp_path / "analytics.db"
    monkeypatch.setattr("analytics_db.ANALYTICS_DB_PATH", db)
    init_analytics_db(db)
    log_event("test_ping", source_id="src-1", persona_key="garden", payload={"n": 1})
    import sqlite3

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT event_type, source_id FROM events ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row[0] == "test_ping"
    assert row[1] == "src-1"
