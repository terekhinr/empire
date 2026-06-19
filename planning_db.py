"""SQLite + Obsidian sync for personal planning (goals, projects, tasks)."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PLANNING_DIR = BASE_DIR / "data" / "planning"
PLANNING_DB_PATH = PLANNING_DIR / "planning.db"
OBSIDIAN_TASKS_DIR = BASE_DIR / "data" / "obsidian_vault" / "Life" / "tasks"
OBSIDIAN_INBOX = OBSIDIAN_TASKS_DIR / "inbox.md"
OBSIDIAN_SYNC_OUT = OBSIDIAN_TASKS_DIR / "dashboard-sync.md"

TASK_LINE_RE = re.compile(
    r"^-\s+\[(?P<done>[ xX])\]\s+(?P<title>.+?)(?:\s*—\s*(?P<note>.*))?\s*$"
)
DUE_RE = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})")
TAG_RE = re.compile(r"#([\w\-А-Яа-яЁё]+)")
PRIORITY_MAP = {"⏫": 3, "🔼": 2, "🔽": 1}

KIND_GOAL = "goal"
KIND_PROJECT = "project"
KIND_TASK = "task"
STATUSES = ("todo", "doing", "done", "cancelled")


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
        """
    )
    conn.commit()
    conn.close()


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


def add_project(title: str, goal_id: int | None = None, description: str = "") -> int:
    init_db()
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO projects (title, goal_id, description, updated_at) VALUES (?, ?, ?, ?)",
        (title.strip(), goal_id, description or None, _now()),
    )
    conn.commit()
    pid = int(cur.lastrowid)
    conn.close()
    return pid


def add_task(
    title: str,
    *,
    kind: str = KIND_TASK,
    project_id: int | None = None,
    goal_id: int | None = None,
    status: str = "todo",
    priority: int = 0,
    due_date: str | None = None,
    tags: list[str] | None = None,
    note: str | None = None,
    obsidian_source: str | None = None,
) -> int:
    init_db()
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO tasks (
            title, kind, project_id, goal_id, status, priority, due_date, tags, note,
            obsidian_source, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title.strip(),
            kind,
            project_id,
            goal_id,
            status,
            priority,
            due_date,
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
    conn.execute(
        "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
        (status, _now(), task_id),
    )
    conn.commit()
    conn.close()


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
    }
    conn.close()
    return out
