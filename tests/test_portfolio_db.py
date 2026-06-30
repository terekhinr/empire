"""Portfolio DB init and locking."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from portfolio import db as pdb


@pytest.fixture()
def tmp_db(tmp_path: Path, monkeypatch):
    path = tmp_path / "portfolio.db"
    monkeypatch.setattr(pdb, "PORTFOLIO_DB", path)
    monkeypatch.setattr(pdb, "_initialized_paths", set())
    return path


def test_init_db_idempotent(tmp_db: Path):
    pdb.init_db()
    pdb.init_db()
    with pdb.db_session() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM brokers").fetchone()
    assert row["c"] >= 1


def test_init_db_with_shared_connection(tmp_db: Path):
    with pdb.db_session() as conn:
        pdb.init_db(conn)
        row = conn.execute("SELECT value FROM settings WHERE key='portfolio_ui_mode'").fetchone()
    assert row["value"] == "snowball"


def test_retry_locked_recovers(monkeypatch):
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "ok"

    assert pdb._retry_locked(flaky, attempts=5, base_delay=0) == "ok"
    assert calls["n"] == 3
