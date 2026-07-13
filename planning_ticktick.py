"""Import TickTick backup CSV into planning.db."""

from __future__ import annotations

import csv
import html
import io
import re
from typing import Any

from planning_db import (
    add_task,
    delete_task,
    ensure_project,
    get_connection,
    init_db,
    load_projects_df,
    planning_ticktick_reset_stats,
    planning_wipe_stats,
    purge_all_planning_data,
    purge_tasks_for_ticktick_import,
    update_task,
)
from planning_ticktick_catalog import (
    catalog_folder_for_list,
    catalog_sort_for_list,
    restore_ticktick_list_catalog,
)
from planning_recurrence import parse_repeat_rule, serialize_repeat_rule

PRIORITY_MAP = {5: 3, 3: 2, 1: 1}

CONTENT_KEYS = (
    "Content",
    "content",
    "Description",
    "description",
    "Note",
    "note",
    "Notes",
    "notes",
    "Memo",
    "memo",
    "Содержание",
    "Описание",
    "Заметка",
)

TITLE_KEYS = ("Title", "title", "Task Title", "task title", "Name", "name")

PARENT_ID_KEYS = ("parentId", "parentid", "Parent ID", "ParentId", "parent id")


def _parse_date(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def _parse_time(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    m = re.search(r"(\d{1,2}):(\d{2})", raw)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return None


def _rrule_to_repeat(rrule: str) -> str | None:
    r = (rrule or "").upper()
    if not r or "FREQ=" not in r:
        return None
    if "DAILY" in r:
        rule = {"freq": "daily", "interval": 1}
    elif "WEEKLY" in r:
        rule = {"freq": "weekly", "interval": 1}
    elif "MONTHLY" in r:
        rule = {"freq": "monthly", "interval": 1}
    elif "YEARLY" in r:
        rule = {"freq": "yearly", "interval": 1}
    else:
        rule = parse_repeat_rule(rrule)
    return serialize_repeat_rule(rule) if rule else None


def _normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {(k or "").strip(): (v or "") for k, v in row.items()}


def _field(row: dict[str, str], *names: str) -> str:
    lowered = {k.lower(): v for k, v in row.items()}
    for name in names:
        if name in row and row[name].strip():
            return row[name].strip()
        val = lowered.get(name.lower(), "")
        if val.strip():
            return val.strip()
    return ""


def _clean_note(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    raw = re.sub(r"</p\s*>", "\n", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html.unescape(raw)
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
    return raw or None


def _extract_note(row: dict[str, str]) -> str | None:
    parts: list[str] = []
    for key in CONTENT_KEYS:
        val = _clean_note(row.get(key, ""))
        if val and val not in parts:
            parts.append(val)
    if not parts:
        for key, val in row.items():
            if key.lower() in {k.lower() for k in CONTENT_KEYS}:
                cleaned = _clean_note(val)
                if cleaned and cleaned not in parts:
                    parts.append(cleaned)
    if not parts:
        return None
    return "\n\n".join(parts)


def _content_col_index(header: list[str]) -> int | None:
    for i, h in enumerate(header):
        key = h.strip().strip('"')
        if key in CONTENT_KEYS or key.lower() in {k.lower() for k in CONTENT_KEYS}:
            return i
    return None


def _align_row(header: list[str], row: list[str]) -> list[str]:
    """Pad short rows; merge overflow fields into Content (unescaped commas)."""
    n = len(header)
    if len(row) < n:
        return row + [""] * (n - len(row))
    if len(row) == n:
        return row
    content_idx = _content_col_index(header)
    if content_idx is None:
        content_idx = n - 1
    extra = len(row) - n
    merged = ",".join(row[content_idx : content_idx + extra + 1])
    return row[:content_idx] + [merged] + row[content_idx + extra + 1 :]


def _find_header_index(rows: list[list[str]]) -> int | None:
    for i, row in enumerate(rows):
        if not row:
            continue
        cells = {c.strip().strip('"') for c in row if c}
        if "Folder Name" in cells and "List Name" in cells and (
            "Title" in cells or "Task Title" in cells
        ):
            return i
    return None


def read_ticktick_csv(text: str) -> list[dict[str, str]]:
    """Parse TickTick CSV preserving multiline quoted Content fields."""
    text = text.lstrip("\ufeff")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    start = _find_header_index(rows)
    if start is None or start >= len(rows) - 1:
        return []

    header = [h.strip().strip('"') for h in rows[start]]
    out: list[dict[str, str]] = []
    for row in rows[start + 1 :]:
        if not row or not any((c or "").strip() for c in row):
            continue
        row = _align_row(header, row)
        out.append(_normalize_row(dict(zip(header, row))))
    return out


def _ticktick_task_id(row: dict[str, str]) -> str:
    return _field(row, "taskId", "taskid", "Task ID", "id")


def _ticktick_parent_id(row: dict[str, str]) -> str | None:
    raw = _field(row, *PARENT_ID_KEYS).strip()
    if not raw or raw in ("0", "null", "NULL"):
        return None
    return raw


def _sort_parents_before_children(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_id = {_ticktick_task_id(r): r for r in rows if _ticktick_task_id(r)}
    ordered: list[dict[str, str]] = []
    seen: set[int] = set()

    def place(row: dict[str, str]) -> None:
        key = id(row)
        if key in seen:
            return
        parent = _ticktick_parent_id(row)
        if parent and parent in by_id:
            place(by_id[parent])
        seen.add(key)
        ordered.append(row)

    for row in rows:
        place(row)
    return ordered


def _project_id_for_list(
    list_name: str,
    cache: dict[str, int],
    *,
    folder_name: str = "",
) -> int | None:
    name = (list_name or "").strip()
    if not name or name.lower() in ("inbox", "tasks", "notes", ""):
        return None
    if name in cache:
        return cache[name]
    df = load_projects_df()
    existing = {row["title"]: int(row["id"]) for _, row in df.iterrows()}
    if name in existing:
        cache[name] = existing[name]
        return existing[name]
    folder = (folder_name or "").strip() or catalog_folder_for_list(name)
    sort_order = catalog_sort_for_list(name)
    pid = ensure_project(name, folder_name=folder, sort_order=sort_order, description="Импорт TickTick")
    cache[name] = pid
    return pid


def _ensure_lists_from_rows(rows: list[dict[str, str]], cache: dict[str, int]) -> None:
    """Создать пустые списки по CSV, даже если все задачи архивные."""
    seen: set[tuple[str, str]] = set()
    for row in rows:
        list_name = _field(row, "List Name", "list name")
        if not list_name or list_name.lower() in ("inbox", "tasks", "notes"):
            continue
        folder_name = _field(row, "Folder Name", "folder name")
        key = (list_name, folder_name)
        if key in seen:
            continue
        seen.add(key)
        _project_id_for_list(list_name, cache, folder_name=folder_name)


def _ticktick_source(row: dict[str, str], title: str, due_date: str | None) -> str:
    task_id = _field(row, "taskId", "taskid", "Task ID", "id")
    if task_id:
        return f"ticktick:id:{task_id}"
    return f"ticktick:{title}:{due_date or ''}"


def _find_task_id_by_title(title: str) -> int | None:
    title = (title or "").strip()
    if not title:
        return None
    init_db()
    conn = get_connection()
    row = conn.execute(
        """
        SELECT id FROM tasks
        WHERE lower(trim(title)) = lower(trim(?))
          AND kind = 'task'
        ORDER BY
          CASE WHEN obsidian_source LIKE 'ticktick:%' THEN 1 ELSE 0 END,
          id ASC
        LIMIT 1
        """,
        (title,),
    ).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def _link_ticktick_source(task_id: int, source: str) -> None:
    if not source.startswith("ticktick:id:"):
        return
    conn = get_connection()
    conn.execute(
        "UPDATE tasks SET obsidian_source = ? WHERE id = ?",
        (source, task_id),
    )
    conn.commit()
    conn.close()


def _find_task_id_by_source(source: str, *, title: str = "", due_date: str | None = None) -> int | None:
    init_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM tasks WHERE obsidian_source = ? ORDER BY id DESC LIMIT 1",
        (source,),
    ).fetchone()
    if row:
        conn.close()
        return int(row["id"])
    legacy = f"ticktick:{title}:{due_date or ''}"
    if legacy != source:
        row = conn.execute(
            "SELECT id FROM tasks WHERE obsidian_source = ? ORDER BY id DESC LIMIT 1",
            (legacy,),
        ).fetchone()
        if row:
            conn.close()
            return int(row["id"])
    conn.close()
    return None


def _backfill_note(task_id: int, note: str | None, *, source: str) -> bool:
    if not note:
        return False
    update_task(task_id, note=note)
    _link_ticktick_source(task_id, source)
    return True


def _resolve_parent_id(
    row: dict[str, str],
    *,
    id_map: dict[str, int],
) -> int | None:
    parent_tid = _ticktick_parent_id(row)
    if not parent_tid:
        return None
    if parent_tid in id_map:
        return id_map[parent_tid]
    found = _find_task_id_by_source(f"ticktick:id:{parent_tid}")
    if found:
        id_map[parent_tid] = found
        return found
    return None


def _parse_priority(row: dict[str, str]) -> int:
    prio_raw = _field(row, "Priority", "priority") or "0"
    prio_raw = re.sub(r"^[pP]", "", prio_raw.strip())
    try:
        return PRIORITY_MAP.get(int(prio_raw), 0)
    except ValueError:
        return 0


def _parse_tags(row: dict[str, str]) -> list[str]:
    return [t.strip() for t in _field(row, "Tags", "tags").replace(",", " ").split() if t.strip()]


def _upsert_ticktick_row(
    row: dict[str, str],
    *,
    project_cache: dict[str, int],
    id_map: dict[str, int],
    update_existing: bool,
) -> tuple[str, int | None]:
    """Returns action and empire task id."""
    status = (_field(row, "Status", "status") or "0").strip()
    if status not in ("0", "1", "2"):
        return "skipped", None
    title = _field(row, *TITLE_KEYS)
    if not title:
        return "skipped", None

    note = _extract_note(row)
    due_raw = _field(row, "Due Date", "due date")
    due_date = _parse_date(due_raw)
    source = _ticktick_source(row, title, due_date)
    existing_id = _find_task_id_by_source(source, title=title, due_date=due_date)
    if not existing_id:
        existing_id = _find_task_id_by_title(title)

    # TickTick completed/archived: enrich existing or import as done (восстанавливает списки).
    if status in ("1", "2"):
        empire_status = "done" if status == "1" else "cancelled"
        if existing_id:
            if note and update_existing:
                if _backfill_note(existing_id, note, source=source):
                    if status == "1":
                        update_task(existing_id, status="done")
                    return "backfilled", existing_id
            if status == "1" and update_existing:
                update_task(existing_id, status="done")
                return "updated", existing_id
            return "skipped", existing_id

        list_name = _field(row, "List Name", "list name")
        folder_name = _field(row, "Folder Name", "folder name")
        project_id = _project_id_for_list(list_name, project_cache, folder_name=folder_name)
        parent_id = _resolve_parent_id(row, id_map=id_map)
        task_id = add_task(
            title,
            project_id=project_id,
            parent_id=parent_id,
            due_date=due_date,
            due_time=_parse_time(due_raw),
            priority=_parse_priority(row),
            tags=_parse_tags(row) or None,
            note=note,
            repeat_rule=_rrule_to_repeat(_field(row, "Repeat", "repeat")),
            obsidian_source=source,
            status=empire_status,
        )
        return "imported_done", task_id

    list_name = _field(row, "List Name", "list name")
    folder_name = _field(row, "Folder Name", "folder name")
    due_time = _parse_time(due_raw)
    priority = _parse_priority(row)
    tags = _parse_tags(row)
    repeat_rule = _rrule_to_repeat(_field(row, "Repeat", "repeat"))
    project_id = _project_id_for_list(list_name, project_cache, folder_name=folder_name)
    parent_id = _resolve_parent_id(row, id_map=id_map)

    update_fields: dict[str, Any] = {
        "title": title,
        "due_date": due_date,
        "due_time": due_time,
        "priority": priority,
        "tags": tags or [],
        "project_id": project_id,
        "repeat_rule": repeat_rule,
        "status": "todo",
    }
    if note is not None:
        update_fields["note"] = note
    if parent_id is not None:
        update_fields["parent_id"] = parent_id

    if existing_id and update_existing:
        update_task(existing_id, **update_fields)
        _link_ticktick_source(existing_id, source)
        return "updated", existing_id
    if existing_id:
        return "skipped", existing_id

    task_id = add_task(
        title,
        project_id=project_id,
        parent_id=parent_id,
        due_date=due_date,
        due_time=due_time,
        priority=priority,
        tags=tags or None,
        note=note,
        repeat_rule=repeat_rule,
        obsidian_source=source,
    )
    return "imported", task_id


def import_ticktick_csv(text: str, *, update_existing: bool = True) -> dict[str, Any]:
    rows = _sort_parents_before_children(read_ticktick_csv(text))
    project_cache: dict[str, int] = {}
    _ensure_lists_from_rows(rows, project_cache)
    id_map: dict[str, int] = {}
    imported = updated = skipped = backfilled = imported_done = 0
    with_notes = 0

    for row in rows:
        note = _extract_note(row)
        if note:
            with_notes += 1
        action, task_id = _upsert_ticktick_row(
            row,
            project_cache=project_cache,
            id_map=id_map,
            update_existing=update_existing,
        )
        if action == "imported":
            imported += 1
        elif action == "imported_done":
            imported_done += 1
        elif action == "updated":
            updated += 1
        elif action == "backfilled":
            backfilled += 1
        else:
            skipped += 1
        tid = _ticktick_task_id(row)
        if task_id and tid:
            id_map[tid] = task_id

    catalog = restore_ticktick_list_catalog(create_shells=True)

    return {
        "imported": imported,
        "imported_done": imported_done,
        "updated": updated,
        "skipped": skipped,
        "backfilled": backfilled,
        "with_notes": with_notes,
        "projects": len(project_cache),
        "catalog": catalog,
    }


def import_ticktick_file(path: str, *, update_existing: bool = True) -> dict[str, Any]:
    text = io.open(path, encoding="utf-8-sig").read()
    return import_ticktick_csv(text, update_existing=update_existing)


PURGE_SCOPE_TICKTICK = "ticktick"
PURGE_SCOPE_REIMPORT = "reimport"
PURGE_SCOPE_ALL = "all"
PURGE_SCOPE_TASKS = "tasks"
PURGE_SCOPE_FULL = "full"


def _purge_scope_sql(scope: str) -> str:
    if scope == PURGE_SCOPE_TICKTICK:
        return "obsidian_source LIKE 'ticktick:%'"
    if scope == PURGE_SCOPE_REIMPORT:
        return (
            "(obsidian_source LIKE 'ticktick:%' OR obsidian_source LIKE '- [%')"
        )
    if scope == PURGE_SCOPE_ALL:
        return "(obsidian_source IS NULL OR obsidian_source NOT LIKE 'empire-audit:%')"
    if scope in (PURGE_SCOPE_TASKS, PURGE_SCOPE_FULL):
        raise ValueError(f"use dedicated purge for scope:{scope}")
    raise ValueError(f"unknown_purge_scope:{scope}")


def ticktick_task_stats(*, scope: str = PURGE_SCOPE_REIMPORT) -> dict[str, int]:
    if scope == PURGE_SCOPE_FULL:
        return planning_wipe_stats()
    if scope == PURGE_SCOPE_TASKS:
        return planning_ticktick_reset_stats()
    init_db()
    where = _purge_scope_sql(scope)
    conn = get_connection()
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS n FROM tasks
        WHERE kind = 'task' AND {where}
        """
    ).fetchone()
    ticktick = conn.execute(
        "SELECT COUNT(*) AS n FROM tasks WHERE kind = 'task' AND obsidian_source LIKE 'ticktick:%'"
    ).fetchone()
    obsidian = conn.execute(
        "SELECT COUNT(*) AS n FROM tasks WHERE kind = 'task' AND obsidian_source LIKE '- [%'"
    ).fetchone()
    conn.close()
    return {
        "count": int(row["n"] if row else 0),
        "ticktick": int(ticktick["n"] if ticktick else 0),
        "obsidian_inbox": int(obsidian["n"] if obsidian else 0),
        "scope": scope,
    }


def purge_ticktick_tasks(*, scope: str = PURGE_SCOPE_REIMPORT) -> dict[str, int]:
    if scope == PURGE_SCOPE_FULL:
        return purge_all_planning_data(include_checklists=True)
    if scope == PURGE_SCOPE_TASKS:
        return purge_tasks_for_ticktick_import()
    init_db()
    where = _purge_scope_sql(scope)
    conn = get_connection()
    rows = conn.execute(
        f"SELECT id FROM tasks WHERE kind = 'task' AND {where} ORDER BY id DESC"
    ).fetchall()
    conn.close()
    deleted = 0
    for row in rows:
        delete_task(int(row["id"]))
        deleted += 1
    return {"deleted": deleted, "scope": scope}
