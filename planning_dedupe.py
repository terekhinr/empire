"""Find and remove duplicate planning tasks (same title + due date)."""

from __future__ import annotations

import re
from typing import Any

from planning_db import delete_task, list_tasks


def _norm_title(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    return t


def _group_key(task: dict[str, Any]) -> str:
    title = _norm_title(task.get("title") or "")
    due = task.get("due_date") or ""
    return f"{title}\0{due}"


def _keeper_score(task: dict[str, Any]) -> tuple[int, int]:
    score = 0
    if task.get("repeat_rule"):
        score += 30
    if (task.get("note") or "").strip():
        score += 15
    src = task.get("obsidian_source") or ""
    if src.startswith("ticktick:id:"):
        score += 10
    elif src.startswith("ticktick:"):
        score += 5
    if task.get("due_time"):
        score += 3
    if task.get("image_path"):
        score += 3
    if task.get("remind_at"):
        score += 2
    # Prefer lower id (older canonical row) on tie.
    return (score, -int(task.get("id") or 0))


def find_duplicate_groups(*, include_done: bool = False) -> list[dict[str, Any]]:
    tasks = list_tasks(include_done=include_done, limit=5000)
    buckets: dict[str, list[dict[str, Any]]] = {}
    for t in tasks:
        if t.get("kind") != "task":
            continue
        if not include_done and t.get("status") in ("done", "cancelled"):
            continue
        key = _group_key(t)
        if not _norm_title(t.get("title") or ""):
            continue
        buckets.setdefault(key, []).append(t)

    groups: list[dict[str, Any]] = []
    for items in buckets.values():
        if len(items) < 2:
            continue
        ranked = sorted(items, key=_keeper_score, reverse=True)
        keep = ranked[0]
        remove = ranked[1:]
        groups.append(
            {
                "title": keep.get("title"),
                "due_date": keep.get("due_date"),
                "keep_id": keep.get("id"),
                "remove_ids": [t["id"] for t in remove],
                "count": len(items),
            }
        )
    groups.sort(key=lambda g: (-g["count"], g.get("title") or ""))
    return groups


def dedupe_tasks(*, include_done: bool = False, dry_run: bool = False) -> dict[str, Any]:
    groups = find_duplicate_groups(include_done=include_done)
    remove_ids: list[int] = []
    for g in groups:
        remove_ids.extend(g["remove_ids"])
    removed = 0
    if not dry_run:
        for tid in remove_ids:
            delete_task(tid)
            removed += 1
    return {
        "groups": len(groups),
        "to_remove": len(remove_ids),
        "removed": removed,
        "dry_run": dry_run,
        "samples": groups[:15],
    }
