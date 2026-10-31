"""Tests for Empire insights briefing."""

from __future__ import annotations

import pytest

import planning_db as pd_db
import planning_insights as pi


@pytest.fixture()
def temp_planning_db(tmp_path, monkeypatch):
    db_dir = tmp_path / "planning"
    db_dir.mkdir()
    db_path = db_dir / "planning.db"
    monkeypatch.setattr(pd_db, "PLANNING_DIR", db_dir)
    monkeypatch.setattr(pd_db, "PLANNING_DB_PATH", db_path)
    monkeypatch.setattr(pd_db, "OBSIDIAN_INBOX", tmp_path / "inbox.md")
    pd_db.init_db()
    yield db_path


def test_build_empire_insights_structure(monkeypatch):
    monkeypatch.setattr(pi, "summary_counts", lambda: {"tasks_todo": 3, "tasks_doing": 1})
    monkeypatch.setattr(pi, "_overdue_tasks", lambda limit=12: [])
    monkeypatch.setattr(
        pi,
        "health_summary",
        lambda: {"measurements_count": 1, "workouts_count": 2, "summary": {"weight_kg": 80}},
    )
    monkeypatch.setattr(pi, "health_stats", lambda period="month": {"workouts_count": 2})
    monkeypatch.setattr(pi, "_pipeline_progress", lambda: {"percent_weighted": 10})
    monkeypatch.setattr(pi, "list_checklists", lambda **kw: [])
    monkeypatch.setattr(pi, "weekly_events_summary", lambda days=7: {"post_published": 1})
    monkeypatch.setattr(pi, "_llm_narrative", lambda s: None)

    data = pi.build_empire_insights(use_llm=False)
    assert "conclusions" in data
    assert len(data["conclusions"]) >= 1
    assert data["tasks"]["tasks_todo"] == 3


def test_build_daily_briefing_has_focus(monkeypatch):
    monkeypatch.setattr(
        pi,
        "build_empire_insights",
        lambda **kw: {"conclusions": ["ok"], "tasks": {}, "health": {}, "pipeline": {}},
    )
    monkeypatch.setattr(
        pi,
        "_tasks_due_between",
        lambda *a, **kw: [{"title": "A", "due_date": "2026-06-24"}],
    )
    monkeypatch.setattr(pi, "_next_milestone", lambda: {"title": "Launch", "due_date": "2026-09-15"})
    monkeypatch.setattr(pi, "_workouts_last_days", lambda d: 0)
    monkeypatch.setattr(pi, "_llm_daily_focus", lambda s: None)

    data = pi.build_daily_briefing(use_llm=False)
    assert data["kind"] == "daily"
    assert len(data["focus_items"]) >= 1
    assert "telegram_preview" in data
    # вехи в боте выкл. по умолчанию
    assert data.get("next_milestone") is None
    assert "Веха" not in " ".join(data.get("focus_items") or [])
    assert "Пайплайн" not in (data.get("telegram_preview") or "")


def test_milestones_can_be_reenabled(monkeypatch):
    monkeypatch.setenv("EMPIRE_INSIGHTS_MILESTONES", "1")
    monkeypatch.setattr(
        pi,
        "build_empire_insights",
        lambda **kw: {
            "conclusions": ["ok"],
            "tasks": {},
            "health": {},
            "pipeline": {"percent_weighted": 5},
        },
    )
    monkeypatch.setattr(
        pi,
        "_tasks_due_between",
        lambda *a, **kw: [{"title": "A", "due_date": "2026-06-24"}],
    )
    monkeypatch.setattr(pi, "_next_milestone", lambda: {"title": "Launch", "due_date": "2026-09-15"})
    monkeypatch.setattr(pi, "_workouts_last_days", lambda d: 2)
    monkeypatch.setattr(pi, "_llm_daily_focus", lambda s: None)

    data = pi.build_daily_briefing(use_llm=False)
    assert data.get("next_milestone", {}).get("title") == "Launch"
    assert any("Веха" in x for x in (data.get("focus_items") or []))


def test_ensure_daily_focus_checklist_idempotent(temp_planning_db, monkeypatch):
    monkeypatch.setattr(pi, "find_checklist_by_ref", pd_db.find_checklist_by_ref)
    monkeypatch.setattr(pi, "create_checklist", pd_db.create_checklist)
    monkeypatch.setattr(pi, "_archive_old_daily_focus", lambda ref: None)

    cid1 = pi.ensure_daily_focus_checklist(["One", "Two"], day="2099-01-01")
    cid2 = pi.ensure_daily_focus_checklist(["Other"], day="2099-01-01")
    assert cid1 == cid2
