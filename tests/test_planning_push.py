"""Tests for Empire Tasks Web Push."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import planning_db as pd_db
from planning_db import (
    add_task,
    clear_reminder,
    init_db,
    list_due_reminders_for_push,
    list_push_subscriptions,
    mark_reminder_pushed,
    save_push_subscription,
    update_task,
)


@pytest.fixture()
def temp_planning_db(tmp_path, monkeypatch):
    db_dir = tmp_path / "planning"
    db_dir.mkdir()
    db_path = db_dir / "planning.db"
    monkeypatch.setattr(pd_db, "PLANNING_DIR", db_dir)
    monkeypatch.setattr(pd_db, "PLANNING_DB_PATH", db_path)
    monkeypatch.setattr(pd_db, "OBSIDIAN_INBOX", tmp_path / "inbox.md")
    init_db()
    yield db_path


def test_push_subscription_roundtrip(temp_planning_db):
    sid = save_push_subscription(
        "https://push.example.com/ep/1",
        "p256dh-key",
        "auth-key",
        user_agent="test",
    )
    assert sid >= 1
    subs = list_push_subscriptions()
    assert len(subs) == 1
    assert subs[0]["endpoint"].endswith("/1")


def test_reminder_push_only_once(temp_planning_db):
    tid = add_task("Call dentist", remind_at="2020-01-01T08:00:00")
    due = list_due_reminders_for_push()
    assert len(due) == 1
    assert due[0]["id"] == tid

    mark_reminder_pushed(tid)
    assert list_due_reminders_for_push() == []

    clear_reminder(tid)
    update_task(tid, remind_at="2020-01-01T09:00:00")
    due2 = list_due_reminders_for_push()
    assert len(due2) == 1


def test_process_due_without_vapid(monkeypatch):
    monkeypatch.delenv("PLANNING_VAPID_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("PLANNING_VAPID_PRIVATE_KEY", raising=False)

    import importlib
    import planning_push as pp

    importlib.reload(pp)
    result = pp.process_due_reminder_pushes()
    assert result["ok"] is False
    assert result["reason"] == "push_not_configured"


def test_push_configured(monkeypatch):
    monkeypatch.setenv("PLANNING_VAPID_PUBLIC_KEY", "BKx-test")
    monkeypatch.setenv("PLANNING_VAPID_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n")

    import importlib
    import planning_push as pp

    importlib.reload(pp)
    assert pp.push_configured() is True
    assert pp.vapid_public_key() == "BKx-test"
