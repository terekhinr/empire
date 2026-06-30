"""Task statistics for Empire PWA."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from planning_db import get_connection, init_db

PERIOD_DAYS = {"week": 7, "month": 30, "quarter": 90}


def _period_start(period: str) -> str:
    days = PERIOD_DAYS.get(period, 30)
    start = date.today() - timedelta(days=days - 1)
    return start.isoformat()


def task_stats(period: str = "month") -> dict[str, Any]:
    init_db()
    since = _period_start(period)
    conn = get_connection()
    completed = conn.execute(
        """
        SELECT COUNT(*) FROM tasks
        WHERE status = 'done'
          AND parent_id IS NULL
          AND date(COALESCE(completed_at, updated_at)) >= ?
        """,
        (since,),
    ).fetchone()[0]
    created = conn.execute(
        """
        SELECT COUNT(*) FROM tasks
        WHERE parent_id IS NULL AND date(created_at) >= ?
        """,
        (since,),
    ).fetchone()[0]
    open_cnt = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status IN ('todo','doing') AND parent_id IS NULL"
    ).fetchone()[0]
    projects = conn.execute(
        """
        SELECT p.id, p.title,
               SUM(CASE WHEN t.status = 'done' THEN 1 ELSE 0 END) AS done_cnt,
               SUM(CASE WHEN t.status IN ('todo','doing') THEN 1 ELSE 0 END) AS open_cnt,
               COUNT(t.id) AS total_cnt
        FROM projects p
        LEFT JOIN tasks t ON t.project_id = p.id AND t.parent_id IS NULL
        WHERE p.status = 'active'
        GROUP BY p.id, p.title
        HAVING total_cnt > 0
        ORDER BY open_cnt DESC, p.title
        """
    ).fetchall()
    checklists = conn.execute(
        """
        SELECT c.id, c.title,
               SUM(CASE WHEN i.status = 'done' THEN 1 ELSE 0 END) AS done_cnt,
               COUNT(i.id) AS total_cnt
        FROM checklists c
        LEFT JOIN checklist_items i ON i.checklist_id = c.id
        WHERE c.status = 'active'
        GROUP BY c.id, c.title
        ORDER BY c.title
        """
    ).fetchall()
    conn.close()
    proj_out = []
    for row in projects:
        total = int(row["total_cnt"] or 0)
        done = int(row["done_cnt"] or 0)
        proj_out.append(
            {
                "id": row["id"],
                "title": row["title"],
                "done": done,
                "open": int(row["open_cnt"] or 0),
                "total": total,
                "pct": round(100 * done / total) if total else 0,
            }
        )
    cl_out = []
    for row in checklists:
        total = int(row["total_cnt"] or 0)
        done = int(row["done_cnt"] or 0)
        cl_out.append(
            {
                "id": row["id"],
                "title": row["title"],
                "done": done,
                "total": total,
                "pct": round(100 * done / total) if total else 0,
            }
        )
    return {
        "period": period,
        "since": since,
        "completed": int(completed),
        "created": int(created),
        "open": int(open_cnt),
        "projects": proj_out,
        "checklists": cl_out,
    }
