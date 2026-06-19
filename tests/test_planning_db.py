"""Tests for planning_db."""

from __future__ import annotations

import pytest

import planning_db as pd_db


@pytest.fixture()
def temp_planning_db(tmp_path, monkeypatch):
    db_dir = tmp_path / "planning"
    db_dir.mkdir()
    db_path = db_dir / "planning.db"
    inbox = db_dir / "inbox.md"
    inbox.write_text(
        "- [ ] Купить молоко 📅 2026-06-01 #дом\n"
        "- [x] Сделано ✅ 2026-05-26\n"
        "- [ ] Ходить на сплавы #Цели\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(pd_db, "PLANNING_DIR", db_dir)
    monkeypatch.setattr(pd_db, "PLANNING_DB_PATH", db_path)
    monkeypatch.setattr(pd_db, "OBSIDIAN_INBOX", inbox)
    monkeypatch.setattr(pd_db, "OBSIDIAN_SYNC_OUT", db_dir / "dashboard-sync.md")
    pd_db.init_db()
    yield db_path


def test_parse_obsidian_line():
    row = pd_db._parse_obsidian_line("- [ ] Задача 📅 2026-06-01 ⏫ #дом")
    assert row is not None
    assert row["title"] == "Задача"
    assert row["due_date"] == "2026-06-01"
    assert row["priority"] == 3
    assert "дом" in row["tags"]


def test_import_and_export(temp_planning_db):
    result = pd_db.import_obsidian_inbox()
    assert result["imported"] >= 2
    assert pd_db.summary_counts()["tasks_todo"] >= 1
    n = pd_db.export_obsidian_sync()
    assert n >= 1
    sync = pd_db.OBSIDIAN_SYNC_OUT.read_text(encoding="utf-8")
    assert "Dashboard sync" in sync


def test_add_entities(temp_planning_db):
    gid = pd_db.add_goal("Похудеть до 95 кг")
    pid = pd_db.add_project("Зал MODIC1", goal_id=gid)
    tid = pd_db.add_task("3 силовые в неделю", project_id=pid, due_date="2026-07-01")
    df = pd_db.load_tasks_df()
    assert len(df) == 1
    pd_db.update_task_status(tid, "doing")
    assert pd_db.load_tasks_df(status="doing").iloc[0]["title"] == "3 силовые в неделю"
