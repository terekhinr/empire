from planning_dedupe import dedupe_tasks, find_duplicate_groups
from planning_db import add_task, delete_task, init_db


def test_find_duplicate_groups_keeps_repeat(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANNING_DB_PATH", str(tmp_path / "planning.db"))
    init_db()
    a = add_task("ГИРЯ Расписание на неделю", due_date="2026-07-28")
    b = add_task(
        "ГИРЯ Расписание на неделю",
        due_date="2026-07-28",
        repeat_rule={"freq": "weekly", "interval": 1},
    )
    groups = find_duplicate_groups()
    assert len(groups) == 1
    assert groups[0]["keep_id"] == b
    assert a in groups[0]["remove_ids"]


def test_dedupe_removes_extras(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANNING_DB_PATH", str(tmp_path / "planning.db"))
    init_db()
    add_task("Dup task", due_date="2026-06-01")
    add_task("Dup task", due_date="2026-06-01")
    res = dedupe_tasks()
    assert res["removed"] == 1
    groups = find_duplicate_groups()
    assert groups == []
