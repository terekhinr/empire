"""SQLite + Obsidian sync for personal planning (goals, projects, tasks)."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from planning_recurrence import (
    extract_obsidian_repeat,
    next_occurrence,
    parse_repeat_rule,
    repeat_label,
    serialize_repeat_rule,
)

BASE_DIR = Path(__file__).resolve().parent
PLANNING_DIR = BASE_DIR / "data" / "planning"
PLANNING_DB_PATH = PLANNING_DIR / "planning.db"
TASK_IMAGES_DIR = PLANNING_DIR / "task_images"
OBSIDIAN_TASKS_DIR = BASE_DIR / "data" / "obsidian_vault" / "Life" / "tasks"
OBSIDIAN_INBOX = OBSIDIAN_TASKS_DIR / "inbox.md"
OBSIDIAN_SYNC_OUT = OBSIDIAN_TASKS_DIR / "dashboard-sync.md"

TASK_LINE_RE = re.compile(
    r"^-\s+\[(?P<done>[ xX])\]\s+(?P<title>.+?)(?:\s*—\s*(?P<note>.*))?\s*$"
)
DUE_RE = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})")
TIME_RE = re.compile(r"🕐\s*(\d{1,2}:\d{2})")
TAG_RE = re.compile(r"#([\w\-А-Яа-яЁё]+)")
PRIORITY_MAP = {"⏫": 3, "🔼": 2, "🔽": 1}

KIND_GOAL = "goal"
KIND_PROJECT = "project"
KIND_TASK = "task"
STATUSES = ("todo", "doing", "done", "cancelled", "archived")
CHECKLIST_STATUSES = ("active", "done", "archived")
ITEM_STATUSES = ("todo", "done", "skipped")
SOURCE_USER = "user"
SOURCE_AGENT = "agent"
SOURCE_OBSIDIAN = "obsidian"


def get_connection() -> sqlite3.Connection:
    PLANNING_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(PLANNING_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            target_date TEXT,
            canvas_md TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            goal_id INTEGER REFERENCES goals(id) ON DELETE SET NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            canvas_md TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'task',
            project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
            goal_id INTEGER REFERENCES goals(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'todo',
            priority INTEGER NOT NULL DEFAULT 0,
            due_date TEXT,
            tags TEXT,
            note TEXT,
            obsidian_source TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);
        CREATE INDEX IF NOT EXISTS idx_tasks_kind ON tasks(kind);

        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            source TEXT NOT NULL DEFAULT 'user',
            agent_ref TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            tags TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_checklists_status ON checklists(status);

        CREATE TABLE IF NOT EXISTS checklist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_id INTEGER NOT NULL REFERENCES checklists(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'todo',
            sort_order INTEGER NOT NULL DEFAULT 0,
            note TEXT,
            task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_checklist_items_cl ON checklist_items(checklist_id);
        """
    )
    _migrate_schema(conn)
    conn.commit()
    conn.close()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    for name, typedef in (
        ("due_time", "TEXT"),
        ("remind_at", "TEXT"),
        ("repeat_rule", "TEXT"),
        ("parent_id", "INTEGER"),
        ("completed_at", "TEXT"),
        ("image_path", "TEXT"),
    ):
        if name not in cols:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} {typedef}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_remind ON tasks(remind_at)")
    if "reminder_pushed_at" not in cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN reminder_pushed_at TEXT")
    proj_cols = {r[1] for r in conn.execute("PRAGMA table_info(projects)").fetchall()}
    for name, typedef in (
        ("folder_name", "TEXT"),
        ("sort_order", "INTEGER NOT NULL DEFAULT 500"),
    ):
        if name not in proj_cols:
            conn.execute(f"ALTER TABLE projects ADD COLUMN {name} {typedef}")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            user_agent TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_push_sub_endpoint ON push_subscriptions(endpoint);

        CREATE TABLE IF NOT EXISTS planning_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def add_goal(title: str, description: str = "", target_date: str | None = None) -> int:
    init_db()
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO goals (title, description, target_date, updated_at) VALUES (?, ?, ?, ?)",
        (title.strip(), description or None, target_date, _now()),
    )
    conn.commit()
    gid = int(cur.lastrowid)
    conn.close()
    return gid


def add_project(
    title: str,
    goal_id: int | None = None,
    description: str = "",
    *,
    folder_name: str | None = None,
    sort_order: int | None = None,
) -> int:
    init_db()
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO projects (title, goal_id, description, folder_name, sort_order, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            title.strip(),
            goal_id,
            description or None,
            folder_name,
            sort_order if sort_order is not None else 500,
            _now(),
        ),
    )
    conn.commit()
    pid = int(cur.lastrowid)
    conn.close()
    return pid


def ensure_project(
    title: str,
    *,
    folder_name: str | None = None,
    sort_order: int | None = None,
    description: str | None = None,
) -> int:
    """Найти или создать список (проект TickTick)."""
    name = (title or "").strip()
    if not name:
        raise ValueError("empty_project_title")
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT id FROM projects WHERE title = ?", (name,)).fetchone()
    if row:
        pid = int(row["id"])
        fields: list[str] = []
        params: list[Any] = []
        if folder_name is not None:
            fields.append("folder_name = ?")
            params.append(folder_name)
        if sort_order is not None:
            fields.append("sort_order = ?")
            params.append(sort_order)
        if description is not None:
            fields.append("description = ?")
            params.append(description)
        if fields:
            fields.append("updated_at = ?")
            params.append(_now())
            params.append(pid)
            conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", params)
            conn.commit()
        conn.close()
        return pid
    conn.close()
    return add_project(
        name,
        description=description or "",
        folder_name=folder_name,
        sort_order=sort_order,
    )


def add_task(
    title: str,
    *,
    kind: str = KIND_TASK,
    project_id: int | None = None,
    goal_id: int | None = None,
    parent_id: int | None = None,
    status: str = "todo",
    priority: int = 0,
    due_date: str | None = None,
    due_time: str | None = None,
    remind_at: str | None = None,
    repeat_rule: str | dict[str, Any] | None = None,
    tags: list[str] | None = None,
    note: str | None = None,
    obsidian_source: str | None = None,
) -> int:
    init_db()
    if isinstance(repeat_rule, dict):
        repeat_rule = serialize_repeat_rule(repeat_rule)
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO tasks (
            title, kind, project_id, goal_id, parent_id, status, priority,
            due_date, due_time, remind_at, repeat_rule, tags, note,
            obsidian_source, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title.strip(),
            kind,
            project_id,
            goal_id,
            parent_id,
            status,
            priority,
            due_date,
            due_time,
            remind_at,
            repeat_rule,
            json.dumps(tags or [], ensure_ascii=False),
            note,
            obsidian_source,
            _now(),
        ),
    )
    conn.commit()
    tid = int(cur.lastrowid)
    conn.close()
    return tid


def update_task_status(task_id: int, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(status)
    init_db()
    conn = get_connection()
    if status == "done":
        conn.execute(
            "UPDATE tasks SET status=?, completed_at=?, updated_at=? WHERE id=?",
            (status, _now(), _now(), task_id),
        )
    elif status in ("todo", "doing"):
        conn.execute(
            "UPDATE tasks SET status=?, completed_at=NULL, updated_at=? WHERE id=?",
            (status, _now(), task_id),
        )
    else:
        # archived / cancelled — keep completed_at if any
        conn.execute(
            "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
            (status, _now(), task_id),
        )
    conn.commit()
    conn.close()


def update_task(task_id: int, **fields: Any) -> None:
    allowed = {
        "title",
        "status",
        "priority",
        "project_id",
        "goal_id",
        "parent_id",
        "due_date",
        "due_time",
        "remind_at",
        "reminder_pushed_at",
        "repeat_rule",
        "tags",
        "note",
        "kind",
        "image_path",
    }
    init_db()
    conn = get_connection()
    parts: list[str] = []
    params: list[Any] = []
    for key, val in fields.items():
        if key not in allowed:
            continue
        if key == "tags" and val is not None:
            val = json.dumps(val, ensure_ascii=False)
        if key == "repeat_rule" and isinstance(val, dict):
            val = serialize_repeat_rule(val)
        if key == "remind_at":
            parts.append("reminder_pushed_at=?")
            params.append(None)
        if key == "status" and val == "done":
            conn.execute(
                "UPDATE tasks SET completed_at=? WHERE id=? AND completed_at IS NULL",
                (_now(), task_id),
            )
        if key == "status" and val in ("todo", "doing"):
            conn.execute(
                "UPDATE tasks SET completed_at=NULL WHERE id=?",
                (task_id,),
            )
        parts.append(f"{key}=?")
        params.append(val)
    if not parts:
        conn.close()
        return
    parts.append("updated_at=?")
    params.append(_now())
    params.append(task_id)
    conn.execute(f"UPDATE tasks SET {', '.join(parts)} WHERE id=?", params)
    conn.commit()
    conn.close()


def delete_task(task_id: int) -> None:
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE parent_id=?", (task_id,))
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()


def planning_wipe_stats() -> dict[str, int]:
    init_db()
    conn = get_connection()
    stats = {
        "count": int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]),
        "tasks": int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]),
        "projects": int(conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]),
        "goals": int(conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]),
        "checklists": int(conn.execute("SELECT COUNT(*) FROM checklists").fetchone()[0]),
        "checklist_items": int(conn.execute("SELECT COUNT(*) FROM checklist_items").fetchone()[0]),
        "scope": "full",
    }
    conn.close()
    return stats


def planning_ticktick_reset_stats() -> dict[str, int]:
    init_db()
    conn = get_connection()
    stats = {
        "count": int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]),
        "tasks": int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]),
        "projects": int(conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]),
        "scope": "tasks",
    }
    conn.close()
    return stats


def purge_tasks_for_ticktick_import() -> dict[str, int]:
    """TickTick re-import: tasks + projects only. Health, goals, checklists stay."""
    init_db()
    before = planning_ticktick_reset_stats()
    conn = get_connection()
    conn.execute("DELETE FROM tasks")
    conn.execute("DELETE FROM projects")
    conn.commit()
    conn.close()
    return {
        "deleted": before["tasks"],
        "tasks": before["tasks"],
        "projects": before["projects"],
        "checklists": 0,
        "scope": "tasks",
    }


def purge_all_planning_data(*, include_checklists: bool = False) -> dict[str, int]:
    """Remove tasks, projects, goals; checklists only if explicitly requested."""
    init_db()
    before = planning_wipe_stats()
    conn = get_connection()
    conn.execute("DELETE FROM tasks")
    conn.execute("DELETE FROM projects")
    conn.execute("DELETE FROM goals")
    if include_checklists:
        conn.execute("DELETE FROM checklist_items")
        conn.execute("DELETE FROM checklists")
    conn.commit()
    conn.close()
    return {
        "deleted": before["tasks"],
        "tasks": before["tasks"],
        "projects": before["projects"],
        "goals": before["goals"],
        "checklists": before["checklists"] if include_checklists else 0,
        "checklist_items": before["checklist_items"] if include_checklists else 0,
        "scope": "full",
    }


def complete_task(task_id: int) -> int | None:
    """Mark task done. Returns new task id if recurrence spawned."""
    task = get_task(task_id, with_subtasks=False)
    if not task:
        return None
    rule = parse_repeat_rule(task.get("repeat_rule"))
    update_task_status(task_id, "done")
    if not rule:
        return None
    nxt = next_occurrence(task.get("due_date"), task.get("due_time"), rule)
    if not nxt:
        return None
    due_date, due_time = nxt
    return add_task(
        task["title"],
        kind=task.get("kind") or KIND_TASK,
        project_id=task.get("project_id"),
        goal_id=task.get("goal_id"),
        priority=int(task.get("priority") or 0),
        due_date=due_date,
        due_time=due_time,
        remind_at=task.get("remind_at"),
        repeat_rule=task.get("repeat_rule"),
        tags=task.get("tags"),
        note=task.get("note"),
    )


def update_canvas(entity: str, entity_id: int, canvas_md: str) -> None:
    init_db()
    table = "goals" if entity == "goal" else "projects"
    conn = get_connection()
    conn.execute(
        f"UPDATE {table} SET canvas_md=?, updated_at=? WHERE id=?",
        (canvas_md, _now(), entity_id),
    )
    conn.commit()
    conn.close()


def load_tasks_df(
    *,
    status: str | None = None,
    kind: str | None = None,
    project_id: int | None = None,
) -> pd.DataFrame:
    init_db()
    conn = get_connection()
    q = """
        SELECT t.*, p.title AS project_title, g.title AS goal_title
        FROM tasks t
        LEFT JOIN projects p ON p.id = t.project_id
        LEFT JOIN goals g ON g.id = t.goal_id
        WHERE 1=1
    """
    params: list[Any] = []
    if status:
        q += " AND t.status = ?"
        params.append(status)
    if kind:
        q += " AND t.kind = ?"
        params.append(kind)
    if project_id:
        q += " AND t.project_id = ?"
        params.append(project_id)
    q += " ORDER BY COALESCE(t.due_date, '9999-12-31'), t.priority DESC, t.id"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


def load_goals_df() -> pd.DataFrame:
    init_db()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM goals ORDER BY status, title", conn)
    conn.close()
    return df


def load_projects_df() -> pd.DataFrame:
    init_db()
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT p.*, g.title AS goal_title
        FROM projects p
        LEFT JOIN goals g ON g.id = p.goal_id
        ORDER BY p.status, p.title
        """,
        conn,
    )
    conn.close()
    return df


def _parse_obsidian_line(line: str) -> dict[str, Any] | None:
    m = TASK_LINE_RE.match(line.strip())
    if not m:
        return None
    title_part = m.group("title").strip()
    done = m.group("done").lower() == "x"
    note = (m.group("note") or "").strip() or None

    due_m = DUE_RE.search(title_part)
    due_date = due_m.group(1) if due_m else None
    title_part = DUE_RE.sub("", title_part).strip()

    time_m = TIME_RE.search(title_part)
    due_time = time_m.group(1) if time_m else None
    if due_time and len(due_time) == 4:
        due_time = "0" + due_time
    title_part = TIME_RE.sub("", title_part).strip()

    title_part, repeat_rule = extract_obsidian_repeat(title_part)
    repeat_serialized = serialize_repeat_rule(repeat_rule) if repeat_rule else None

    priority = 0
    for sym, val in PRIORITY_MAP.items():
        if sym in title_part:
            priority = val
            title_part = title_part.replace(sym, "").strip()

    tags = TAG_RE.findall(title_part)
    title_clean = TAG_RE.sub("", title_part).strip()
    title_clean = re.sub(r"\s{2,}", " ", title_clean)

    kind = KIND_TASK
    tag_lower = {t.lower() for t in tags}
    if "цели" in tag_lower or title_clean.lower().startswith("цель:"):
        kind = KIND_GOAL
    elif "проекты" in tag_lower or "проект" in title_clean.lower()[:12]:
        kind = KIND_PROJECT

    return {
        "title": title_clean,
        "status": "done" if done else "todo",
        "due_date": due_date,
        "due_time": due_time,
        "repeat_rule": repeat_serialized,
        "priority": priority,
        "tags": tags,
        "note": note,
        "kind": kind,
        "obsidian_source": line.strip(),
    }


def import_obsidian_inbox(path: Path | None = None) -> dict[str, int]:
    init_db()
    path = path or OBSIDIAN_INBOX
    if not path.exists():
        return {"imported": 0, "skipped": 0, "missing": 1}

    conn = get_connection()
    existing = {
        r[0]
        for r in conn.execute(
            "SELECT obsidian_source FROM tasks WHERE obsidian_source IS NOT NULL"
        ).fetchall()
    }
    conn.close()
    imported = skipped = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_obsidian_line(line)
        if not parsed:
            continue
        src = parsed["obsidian_source"]
        if src in existing:
            skipped += 1
            continue
        add_task(
            parsed["title"],
            kind=parsed["kind"],
            status=parsed["status"],
            priority=parsed["priority"],
            due_date=parsed["due_date"],
            due_time=parsed.get("due_time"),
            repeat_rule=parsed.get("repeat_rule"),
            tags=parsed["tags"],
            note=parsed["note"],
            obsidian_source=src,
        )
        imported += 1
    return {"imported": imported, "skipped": skipped}


def export_obsidian_sync(path: Path | None = None) -> int:
    """Write open dashboard tasks to Obsidian markdown."""
    path = path or OBSIDIAN_SYNC_OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    df = load_tasks_df(status="todo")
    df = pd.concat([df, load_tasks_df(status="doing")], ignore_index=True)
    lines = [
        "# Dashboard sync",
        "",
        f"_Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        "## Активные задачи",
        "",
    ]
    for _, row in df.sort_values(["due_date", "priority"], ascending=[True, False]).iterrows():
        chk = "x" if row["status"] == "done" else " "
        line = f"- [{chk}] {row['title']}"
        if pd.notna(row.get("due_date")) and row["due_date"]:
            line += f" 📅 {row['due_date']}"
        if pd.notna(row.get("due_time")) and row.get("due_time"):
            line += f" 🕐 {row['due_time']}"
        rr = row.get("repeat_rule")
        if pd.notna(rr) and rr:
            try:
                line += f" 🔁 {repeat_label(parse_repeat_rule(str(rr)))}"
            except Exception:
                pass
        if row.get("priority", 0) == 3:
            line += " ⏫"
        elif row.get("priority", 0) == 2:
            line += " 🔼"
        elif row.get("priority", 0) == 1:
            line += " 🔽"
        tags = row.get("tags")
        if tags:
            try:
                for t in json.loads(tags):
                    line += f" #{t}"
            except json.JSONDecodeError:
                pass
        if row.get("project_title"):
            line += f" — _{row['project_title']}_"
        lines.append(line)
    lines.extend(["", "## Цели", ""])
    for _, g in load_goals_df().iterrows():
        if g["status"] == "active":
            lines.append(f"- [ ] {g['title']} #Цели")
    lines.extend(["", "## Проекты", ""])
    for _, p in load_projects_df().iterrows():
        if p["status"] == "active":
            lines.append(f"- [ ] {p['title']} #Проекты")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(df)


def summary_counts() -> dict[str, int]:
    init_db()
    conn = get_connection()
    out = {
        "tasks_todo": conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='todo'"
        ).fetchone()[0],
        "tasks_doing": conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='doing'"
        ).fetchone()[0],
        "tasks_done": conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='done'"
        ).fetchone()[0],
        "goals_active": conn.execute(
            "SELECT COUNT(*) FROM goals WHERE status='active'"
        ).fetchone()[0],
        "projects_active": conn.execute(
            "SELECT COUNT(*) FROM projects WHERE status='active'"
        ).fetchone()[0],
        "checklists_active": conn.execute(
            "SELECT COUNT(*) FROM checklists WHERE status='active'"
        ).fetchone()[0],
    }
    conn.close()
    return out


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except json.JSONDecodeError:
        return []


def task_to_dict(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    d = dict(row) if not isinstance(row, sqlite3.Row) else _row_to_dict(row)
    d["tags"] = _parse_tags(d.get("tags"))
    rule = parse_repeat_rule(d.get("repeat_rule"))
    d["repeat_rule_obj"] = rule
    d["repeat_label"] = repeat_label(rule)
    if d.get("image_path"):
        d["image_url"] = f"/tasks/api/planning/tasks/{d['id']}/image"
    else:
        d["image_url"] = None
    return d


def set_task_image_path(task_id: int, image_path: str | None) -> None:
    update_task(task_id, image_path=image_path)


def get_task_image_file(task_id: int) -> Path | None:
    task = get_task(task_id, with_subtasks=False)
    if not task or not task.get("image_path"):
        return None
    path = TASK_IMAGES_DIR / task["image_path"]
    return path if path.is_file() else None


def list_projects(*, active_only: bool = True) -> list[dict[str, Any]]:
    init_db()
    conn = get_connection()
    q = "SELECT p.*, g.title AS goal_title FROM projects p LEFT JOIN goals g ON g.id = p.goal_id"
    if active_only:
        q += " WHERE p.status='active'"
    q += """
        ORDER BY
            CASE COALESCE(p.folder_name, '')
                WHEN 'ЛИЧНЫЕ ЦЕЛИ' THEN 1
                WHEN 'Архивный список' THEN 2
                WHEN 'Empire' THEN 3
                ELSE 4
            END,
            COALESCE(p.sort_order, 500),
            p.title
    """
    rows = conn.execute(q).fetchall()
    out = []
    for row in rows:
        d = _row_to_dict(row)
        cnt = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE project_id=? AND status IN ('todo','doing')",
            (d["id"],),
        ).fetchone()[0]
        d["open_tasks"] = int(cnt)
        out.append(d)
    conn.close()
    return out


def list_tasks(
    *,
    status: str | None = None,
    include_done: bool = False,
    project_id: int | None = None,
    parent_id: int | None = 0,
    q: str | None = None,
    tag: str | None = None,
    limit: int = 2000,
) -> list[dict[str, Any]]:
    init_db()
    conn = get_connection()
    sql = """
        SELECT t.*, p.title AS project_title, g.title AS goal_title
        FROM tasks t
        LEFT JOIN projects p ON p.id = t.project_id
        LEFT JOIN goals g ON g.id = t.goal_id
        WHERE t.kind = 'task'
    """
    params: list[Any] = []
    if parent_id is not None:
        if parent_id == 0:
            sql += " AND (t.parent_id IS NULL OR t.parent_id = 0)"
        else:
            sql += " AND t.parent_id = ?"
            params.append(parent_id)
    if status:
        sql += " AND t.status = ?"
        params.append(status)
    elif not include_done:
        sql += " AND t.status IN ('todo', 'doing')"
    if project_id:
        sql += " AND t.project_id = ?"
        params.append(project_id)
    if q:
        sql += " AND (t.title LIKE ? OR t.note LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    if tag:
        sql += " AND t.tags LIKE ?"
        params.append(f'%"{tag}"%')
    sql += """
        ORDER BY
            COALESCE(t.due_date, '9999-12-31'),
            COALESCE(t.due_time, '99:99'),
            t.priority DESC,
            t.id
        LIMIT ?
    """
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [task_to_dict(r) for r in rows]


def get_task(task_id: int, *, with_subtasks: bool = True) -> dict[str, Any] | None:
    init_db()
    conn = get_connection()
    row = conn.execute(
        """
        SELECT t.*, p.title AS project_title, g.title AS goal_title
        FROM tasks t
        LEFT JOIN projects p ON p.id = t.project_id
        LEFT JOIN goals g ON g.id = t.goal_id
        WHERE t.id = ?
        """,
        (task_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    out = task_to_dict(row)
    if with_subtasks:
        out["subtasks"] = list_tasks(parent_id=task_id, include_done=True, limit=50)
    return out


def list_due_reminders(*, before_iso: str | None = None) -> list[dict[str, Any]]:
    """Tasks with remind_at <= now and not done."""
    init_db()
    conn = get_connection()
    now = before_iso or _now()
    rows = conn.execute(
        """
        SELECT t.*, p.title AS project_title
        FROM tasks t
        LEFT JOIN projects p ON p.id = t.project_id
        WHERE t.remind_at IS NOT NULL
          AND t.remind_at <= ?
          AND t.status IN ('todo', 'doing')
        ORDER BY t.remind_at
        LIMIT 100
        """,
        (now,),
    ).fetchall()
    conn.close()
    return [task_to_dict(r) for r in rows]


def list_due_reminders_for_push(*, before_iso: str | None = None) -> list[dict[str, Any]]:
    """Due reminders not yet sent via Web Push."""
    init_db()
    conn = get_connection()
    now = before_iso or _now()
    rows = conn.execute(
        """
        SELECT t.*, p.title AS project_title
        FROM tasks t
        LEFT JOIN projects p ON p.id = t.project_id
        WHERE t.remind_at IS NOT NULL
          AND t.remind_at <= ?
          AND t.reminder_pushed_at IS NULL
          AND t.status IN ('todo', 'doing')
        ORDER BY t.remind_at
        LIMIT 50
        """,
        (now,),
    ).fetchall()
    conn.close()
    return [task_to_dict(r) for r in rows]


def mark_reminder_pushed(task_id: int) -> None:
    init_db()
    conn = get_connection()
    conn.execute(
        "UPDATE tasks SET reminder_pushed_at = ?, updated_at = ? WHERE id = ?",
        (_now(), _now(), task_id),
    )
    conn.commit()
    conn.close()


def clear_reminder(task_id: int) -> None:
    update_task(task_id, remind_at=None, reminder_pushed_at=None)


def create_checklist(
    title: str,
    *,
    description: str | None = None,
    source: str = SOURCE_USER,
    agent_ref: str | None = None,
    tags: list[str] | None = None,
    items: list[str] | None = None,
) -> int:
    init_db()
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO checklists (title, description, source, agent_ref, tags, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            title.strip(),
            description,
            source,
            agent_ref,
            json.dumps(tags or [], ensure_ascii=False),
            _now(),
        ),
    )
    cid = int(cur.lastrowid)
    for i, item_title in enumerate(items or []):
        conn.execute(
            """
            INSERT INTO checklist_items (checklist_id, title, sort_order, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (cid, item_title.strip(), i, _now()),
        )
    conn.commit()
    conn.close()
    return cid


def get_checklist(checklist_id: int, *, include_items: bool = True) -> dict[str, Any] | None:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT * FROM checklists WHERE id = ?", (checklist_id,)).fetchone()
    if not row:
        conn.close()
        return None
    out = _row_to_dict(row)
    out["tags"] = _parse_tags(out.get("tags"))
    if include_items:
        items = conn.execute(
            """
            SELECT * FROM checklist_items
            WHERE checklist_id = ?
            ORDER BY sort_order, id
            """,
            (checklist_id,),
        ).fetchall()
        out["items"] = [_row_to_dict(i) for i in items]
        out["items_done"] = sum(1 for i in out["items"] if i["status"] == "done")
        out["items_total"] = len(out["items"])
    conn.close()
    return out


def find_checklist_by_ref(agent_ref: str) -> dict[str, Any] | None:
    init_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM checklists WHERE agent_ref = ? ORDER BY id DESC LIMIT 1",
        (agent_ref,),
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def list_checklists(
    *,
    status: str | None = "active",
    source: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    init_db()
    conn = get_connection()
    q = "SELECT * FROM checklists WHERE 1=1"
    params: list[Any] = []
    if status:
        q += " AND status = ?"
        params.append(status)
    if source:
        q += " AND source = ?"
        params.append(source)
    q += " ORDER BY updated_at DESC, id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        cl = _row_to_dict(row)
        cl["tags"] = _parse_tags(cl.get("tags"))
        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done
            FROM checklist_items WHERE checklist_id = ?
            """,
            (cl["id"],),
        ).fetchone()
        cl["items_total"] = int(stats["total"] or 0)
        cl["items_done"] = int(stats["done"] or 0)
        out.append(cl)
    conn.close()
    return out


def update_checklist_item_status(item_id: int, status: str) -> None:
    if status not in ITEM_STATUSES:
        raise ValueError(status)
    init_db()
    conn = get_connection()
    conn.execute(
        "UPDATE checklist_items SET status=?, updated_at=? WHERE id=?",
        (status, _now(), item_id),
    )
    row = conn.execute(
        "SELECT checklist_id FROM checklist_items WHERE id = ?", (item_id,)
    ).fetchone()
    if row:
        cid = int(row["checklist_id"])
        pending = conn.execute(
            """
            SELECT COUNT(*) FROM checklist_items
            WHERE checklist_id = ? AND status = 'todo'
            """,
            (cid,),
        ).fetchone()[0]
        if pending == 0:
            conn.execute(
                "UPDATE checklists SET status='done', updated_at=? WHERE id=?",
                (_now(), cid),
            )
        else:
            conn.execute(
                "UPDATE checklists SET updated_at=? WHERE id=?",
                (_now(), cid),
            )
    conn.commit()
    conn.close()


def update_checklist_status(checklist_id: int, status: str) -> None:
    if status not in CHECKLIST_STATUSES:
        raise ValueError(status)
    init_db()
    conn = get_connection()
    conn.execute(
        "UPDATE checklists SET status=?, updated_at=? WHERE id=?",
        (status, _now(), checklist_id),
    )
    conn.commit()
    conn.close()


CHECKLIST_ITEM_RE = re.compile(
    r"^-\s+\[(?P<done>[ xX])\]\s+(?P<title>.+?)\s*$"
)


def parse_checklist_markdown(text: str) -> dict[str, Any]:
    """Parse markdown checklist: # title, body, - [ ] items."""
    lines = text.strip().splitlines()
    title = "Чеклист"
    description_lines: list[str] = []
    items: list[dict[str, str]] = []
    in_items = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            continue
        m = CHECKLIST_ITEM_RE.match(stripped)
        if m:
            in_items = True
            items.append(
                {
                    "title": m.group("title").strip(),
                    "status": "done" if m.group("done").lower() == "x" else "todo",
                }
            )
            continue
        if not in_items:
            description_lines.append(stripped)
    return {
        "title": title,
        "description": "\n".join(description_lines) or None,
        "items": items,
    }


def create_checklist_from_markdown(
    text: str,
    *,
    source: str = SOURCE_AGENT,
    agent_ref: str | None = None,
    tags: list[str] | None = None,
) -> int:
    parsed = parse_checklist_markdown(text)
    init_db()
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO checklists (title, description, source, agent_ref, tags, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            parsed["title"],
            parsed["description"],
            source,
            agent_ref,
            json.dumps(tags or [], ensure_ascii=False),
            _now(),
        ),
    )
    cid = int(cur.lastrowid)
    for i, item in enumerate(parsed["items"]):
        conn.execute(
            """
            INSERT INTO checklist_items (checklist_id, title, status, sort_order, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (cid, item["title"], item["status"], i, _now()),
        )
    conn.commit()
    conn.close()
    return cid


def save_push_subscription(
    endpoint: str,
    p256dh: str,
    auth: str,
    *,
    user_agent: str | None = None,
) -> int:
    init_db()
    conn = get_connection()
    now = _now()
    cur = conn.execute(
        """
        INSERT INTO push_subscriptions (endpoint, p256dh, auth, user_agent, created_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(endpoint) DO UPDATE SET
            p256dh=excluded.p256dh,
            auth=excluded.auth,
            user_agent=excluded.user_agent,
            last_seen_at=excluded.last_seen_at
        """,
        (endpoint, p256dh, auth, user_agent, now, now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM push_subscriptions WHERE endpoint = ?", (endpoint,)
    ).fetchone()
    sid = int(row["id"]) if row else int(cur.lastrowid)
    conn.close()
    return sid


def delete_push_subscription(endpoint: str) -> bool:
    init_db()
    conn = get_connection()
    cur = conn.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def list_push_subscriptions() -> list[dict[str, Any]]:
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, endpoint, p256dh, auth, user_agent, created_at, last_seen_at FROM push_subscriptions ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def prune_push_subscriptions(*, max_age_days: int = 120) -> int:
    init_db()
    conn = get_connection()
    cur = conn.execute(
        """
        DELETE FROM push_subscriptions
        WHERE datetime(last_seen_at) < datetime('now', ?)
        """,
        (f"-{max_age_days} days",),
    )
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n


def get_planning_setting(key: str, default: str = "") -> str:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT value FROM planning_settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_planning_setting(key: str, value: str) -> None:
    init_db()
    conn = get_connection()
    conn.execute(
        "INSERT INTO planning_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()
