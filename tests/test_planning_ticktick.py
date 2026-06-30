"""Tests for TickTick CSV import."""

from __future__ import annotations

import pytest

import planning_db as pd_db
import planning_ticktick as pt


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


def test_read_multiline_quoted_content():
    text = '''"Folder Name","List Name","Title","Tags","Content","Status","taskId"
"","Inbox","Note task","","Line one
Line two","0","42"
'''
    rows = pt.read_ticktick_csv(text)
    assert len(rows) == 1
    assert pt._extract_note(rows[0]) == "Line one\nLine two"


def test_align_unquoted_commas_in_content():
    text = """Folder Name,List Name,Title,Tags,Content,Is Check list,Status,taskId,parentId
,Inbox,Test,,Hello, world, with commas,N,0,1,
"""
    rows = pt.read_ticktick_csv(text)
    assert len(rows) == 1
    assert rows[0]["Content"] == "Hello, world, with commas"
    assert rows[0]["Is Check list"] == "N"
    assert rows[0]["taskId"] == "1"


def test_import_sets_note_and_reimport_preserves_note(temp_planning_db):
    text = """Folder Name,List Name,Title,Tags,Content,Status,taskId
,Inbox,First,,Alpha note,0,100
"""
    r1 = pt.import_ticktick_csv(text)
    assert r1["imported"] == 1
    assert r1["with_notes"] == 1
    task = pd_db.list_tasks()[0]
    assert task["note"] == "Alpha note"
    assert task["obsidian_source"] == "ticktick:id:100"

    text2 = """Folder Name,List Name,Title,Tags,Content,Status,taskId
,Inbox,First,,,0,100
"""
    r2 = pt.import_ticktick_csv(text2)
    assert r2["updated"] == 1
    task2 = pd_db.get_task(task["id"])
    assert task2["note"] == "Alpha note"


def test_archived_backfills_existing_task_by_title(temp_planning_db):
    pd_db.add_task("Макс говорит", obsidian_source="- [ ] Макс говорит")
    text = """Folder Name,List Name,Title,Kind,Tags,Content,Status,taskId
,Позже,Макс говорит,TEXT,,Пунюк - мячик попрыгун,2,99
"""
    r = pt.import_ticktick_csv(text)
    assert r["backfilled"] == 1
    task = pd_db.list_tasks()[0]
    assert "Пунюк" in (task["note"] or "")
    assert task["obsidian_source"] == "ticktick:id:99"


def test_purge_tasks_for_ticktick_import(temp_planning_db):
    text = """Folder Name,List Name,Title,Tags,Content,Status,taskId
,Inbox,Tick one,,Note,0,50
"""
    pt.import_ticktick_csv(text)
    pd_db.add_project("Ручной проект")
    pd_db.create_checklist("Список", items=["Пункт"])
    manual = pd_db.add_task("Своя", obsidian_source="manual:1")
    assert pd_db.planning_ticktick_reset_stats()["tasks"] >= 2
    res = pd_db.purge_tasks_for_ticktick_import()
    assert res["tasks"] >= 2
    assert pd_db.planning_ticktick_reset_stats()["tasks"] == 0
    assert len(pd_db.list_checklists()) == 1
    assert pd_db.get_task(manual) is None  # all tasks gone


def test_purge_all_planning_data(temp_planning_db):
    text = """Folder Name,List Name,Title,Tags,Content,Status,taskId
,Inbox,Tick one,,Note,0,50
"""
    pt.import_ticktick_csv(text)
    pd_db.add_project("Ручной проект")
    pd_db.create_checklist("Список", items=["Пункт"])
    assert pd_db.planning_wipe_stats()["tasks"] >= 1
    res = pd_db.purge_all_planning_data(include_checklists=True)
    assert res["tasks"] >= 1
    assert res["projects"] >= 1
    assert res["checklists"] >= 1
    stats = pd_db.planning_wipe_stats()
    assert stats["tasks"] == 0
    assert stats["projects"] == 0
    assert stats["checklists"] == 0


def test_purge_ticktick_tasks(temp_planning_db):
    text = """Folder Name,List Name,Title,Tags,Content,Status,taskId
,Inbox,Tick one,,Note,0,50
,Inbox,Tick two,,,0,51
"""
    pt.import_ticktick_csv(text)
    pd_db.add_task("Своя задача", obsidian_source="manual:1")
    pd_db.add_task("Из Obsidian", obsidian_source="- [ ] Из Obsidian")
    pd_db.add_task("Веха", obsidian_source="empire-audit:milestone:2026-01-01:test")
    stats = pt.ticktick_task_stats(scope=pt.PURGE_SCOPE_REIMPORT)
    assert stats["count"] == 3
    assert stats["ticktick"] == 2
    assert stats["obsidian_inbox"] == 1
    res = pt.purge_ticktick_tasks(scope=pt.PURGE_SCOPE_REIMPORT)
    assert res["deleted"] == 3
    tasks = pd_db.list_tasks(include_done=True)
    assert len(tasks) == 2
    titles = {t["title"] for t in tasks}
    assert titles == {"Своя задача", "Веха"}


def test_purge_all_keeps_audit_milestones(temp_planning_db):
    pd_db.add_task("Ручная", obsidian_source=None)
    pd_db.add_task("Веха", obsidian_source="empire-audit:milestone:2026-01-01:x")
    pd_db.add_task("Inbox", obsidian_source="- [ ] Inbox")
    res = pt.purge_ticktick_tasks(scope=pt.PURGE_SCOPE_ALL)
    assert res["deleted"] == 2
    left = {t["title"] for t in pd_db.list_tasks(include_done=True)}
    assert left == {"Веха"}


def test_fresh_import_skips_update(temp_planning_db):
    text = """Folder Name,List Name,Title,Tags,Content,Status,taskId
,Inbox,Only one,,First note,0,77
"""
    pt.import_ticktick_csv(text)
    pt.purge_ticktick_tasks()
    r = pt.import_ticktick_csv(text, update_existing=False)
    assert r["imported"] == 1
    assert r["updated"] == 0
    task = pd_db.list_tasks()[0]
    assert task["obsidian_source"] == "ticktick:id:77"


def test_import_child_as_subtask(temp_planning_db):
    text = """Folder Name,List Name,Title,Tags,Content,Status,taskId,parentId
,Inbox,Parent,,Parent body,0,10,
,Inbox,Child item,,Child body,0,11,10
"""
    pt.import_ticktick_csv(text)
    parents = pd_db.list_tasks(parent_id=0)
    assert len(parents) == 1
    assert parents[0]["title"] == "Parent"
    assert parents[0]["note"] == "Parent body"
    subs = pd_db.list_tasks(parent_id=parents[0]["id"], include_done=True)
    assert len(subs) == 1
    assert subs[0]["title"] == "Child item"
    assert subs[0]["note"] == "Child body"
