"""Tests for Задачник AI assistant + archive/someday."""

from __future__ import annotations

import asyncio

import pytest

import planning_assistant as pa
import planning_db as pd_db


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


def test_search_and_someday(temp_planning_db):
    pd_db.add_task("Купить гирю", due_date="2026-08-01")
    pd_db.add_task("Идея книги", due_date=None)
    pd_db.add_task("Другое", due_date="2026-08-02")
    found = pa.search_tasks("гир")
    assert any("гир" in t["title"].lower() for t in found)
    someday = pa.list_someday()
    assert len(someday) == 1
    assert someday[0]["title"] == "Идея книги"


def test_archive_done(temp_planning_db):
    tid = pd_db.add_task("Сделано", due_date="2026-07-01")
    pd_db.complete_task(tid)
    n = pa.archive_all_done()
    assert n == 1
    row = pd_db.get_task(tid, with_subtasks=False)
    assert row["status"] == "archived"


def test_assistant_local_find(temp_planning_db, monkeypatch):
    pd_db.add_task("Проверить TRX", due_date="2026-08-10")
    res = asyncio.run(pa.run_assistant("найди TRX"))
    assert res["matches"]
    assert "TRX" in res["matches"][0]["title"]


def test_assistant_local_create(temp_planning_db):
    res = asyncio.run(pa.run_assistant("создай задачу позвонить врачу завтра"))
    assert res["model"] == "local"
    assert res["created"]
    assert "позвонить врачу" in res["created"][0]["title"].lower()
    assert res["created"][0]["due_date"]


def test_assistant_apply_create(temp_planning_db, monkeypatch):
    async def fake_chat(*a, **k):
        return (
            "fake",
            '{"reply":"Создал","search":null,"create":[{"title":"Позвонить врачу","due_date":"завтра","priority":2}],'
            '"complete_ids":null,"archive_done":false}',
            {},
        )

    monkeypatch.setattr(pa, "ASSISTANT_MODELS", ["fake"])
    import tools.llm_client as llm

    monkeypatch.setattr(llm, "chat_with_fallback", fake_chat)
    # без префикса «создай …» — иначе сработает локальный fast-path
    res = asyncio.run(pa.run_assistant("нужна задача: позвонить врачу завтра"))
    assert res["created"]
    assert res["created"][0]["title"] == "Позвонить врачу"
    assert res["created"][0]["due_date"]
