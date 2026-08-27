"""ИИ-ассистент Задачника: поиск и создание задач через LLM + tools."""

from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import date, timedelta
from typing import Any

from planning_db import (
    add_task,
    complete_task,
    get_task,
    list_projects,
    list_tasks,
    update_task_status,
)

ASSISTANT_MODELS = [
    m.strip()
    for m in (
        os.getenv("ZADACHNIK_ASSISTANT_MODEL")
        or os.getenv("PLANNING_ASSISTANT_MODEL")
        or "deepseek/deepseek-chat,mistralai/mistral-small-3.1-24b-instruct,qwen/qwen3-235b-a22b"
    ).split(",")
    if m.strip()
]

_JSON_RE = re.compile(r"\{[\s\S]*\}")


def _today() -> date:
    return date.today()


def _parse_due(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s or s in ("null", "none", "-", "someday", "когда-нибудь"):
        return None
    today = _today()
    if s in ("сегодня", "today"):
        return today.isoformat()
    if s in ("завтра", "tomorrow"):
        return (today + timedelta(days=1)).isoformat()
    if s in ("послезавтра",):
        return (today + timedelta(days=2)).isoformat()
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    return None


def _task_brief(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": t.get("id"),
        "title": t.get("title"),
        "due_date": t.get("due_date"),
        "due_time": t.get("due_time"),
        "priority": t.get("priority"),
        "status": t.get("status"),
        "project": t.get("project_title"),
        "tags": t.get("tags") or [],
    }


def search_tasks(query: str, *, limit: int = 25) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return [_task_brief(t) for t in list_tasks(include_done=False)[:limit]]
    found = list_tasks(q=q, include_done=True)
    out = []
    for t in found:
        if t.get("status") in ("cancelled", "archived"):
            continue
        out.append(_task_brief(t))
        if len(out) >= limit:
            break
    if out:
        return out
    needle = q.lower()
    for t in list_tasks(include_done=False):
        blob = f"{t.get('title','')} {t.get('note') or ''} {' '.join(t.get('tags') or [])}".lower()
        if needle in blob:
            out.append(_task_brief(t))
        if len(out) >= limit:
            break
    return out


def list_someday(*, limit: int = 100) -> list[dict[str, Any]]:
    out = []
    for t in list_tasks(include_done=False):
        if not t.get("due_date"):
            out.append(_task_brief(t))
        if len(out) >= limit:
            break
    return out


def archive_task(task_id: int) -> dict[str, Any] | None:
    row = get_task(task_id, with_subtasks=False)
    if not row:
        return None
    update_task_status(task_id, "archived")
    return get_task(task_id, with_subtasks=False)


def archive_all_done(*, limit: int = 500) -> int:
    n = 0
    for t in list_tasks(status="done", include_done=True)[:limit]:
        update_task_status(int(t["id"]), "archived")
        n += 1
    return n


def _context_snippet(limit: int = 40) -> str:
    open_tasks = list_tasks(include_done=False)[:limit]
    overdue = []
    today = _today().isoformat()
    lines = []
    for t in open_tasks:
        due = t.get("due_date") or "без срока"
        if t.get("due_date") and t["due_date"] < today:
            overdue.append(t)
        lines.append(f"- #{t['id']} [{due}] p{t.get('priority',0)} {t['title']}")
    projects = [f"#{p['id']} {p['title']}" for p in list_projects(active_only=True)[:20]]
    return (
        f"Сегодня: {today}\n"
        f"Открытых: {len(open_tasks)}, просрочено: {len(overdue)}\n"
        f"Проекты: {', '.join(projects) or '—'}\n"
        f"Задачи:\n" + ("\n".join(lines) if lines else "(пусто)")
    )


def _system_prompt() -> str:
    return (
        "Ты ассистент приложения «Задачник». Помогаешь быстро найти и создать задачи.\n"
        "Отвечай ТОЛЬКО валидным JSON без markdown и без пояснений вне JSON:\n"
        "{\n"
        '  "reply": "краткий ответ пользователю по-русски",\n'
        '  "search": "строка поиска или null",\n'
        '  "create": [{"title":"...","due_date":"YYYY-MM-DD|null","due_time":"HH:MM|null",'
        '"priority":0,"note":null,"project_id":null,"someday":false}] или null,\n'
        '  "complete_ids": [id,...] или null,\n'
        '  "archive_done": false\n'
        "}\n"
        "Правила:\n"
        "- Если пользователь ищет — заполни search (ключевые слова).\n"
        "- Если просит создать — create с понятным title; даты: сегодня/завтра → ISO; "
        "«когда-нибудь» → someday:true и due_date:null.\n"
        "- priority: 0 обычный, 2 средний, 3 высокий.\n"
        "- complete_ids только если явно просят закрыть задачу и id известен из контекста.\n"
        "- archive_done:true только если просят перенести выполненные в архив.\n"
        "- Не выдумывай id задач.\n\n"
        f"Контекст:\n{_context_snippet()}"
    )


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _JSON_RE.search(text)
    if not m:
        return {"reply": text[:500], "search": None, "create": None}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"reply": text[:500]}


def _apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    created: list[dict[str, Any]] = []
    completed: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    archived_n = 0

    search_q = plan.get("search")
    if isinstance(search_q, str) and search_q.strip():
        matches = search_tasks(search_q.strip())

    create_items = plan.get("create") or []
    if isinstance(create_items, dict):
        create_items = [create_items]
    for item in create_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        someday = bool(item.get("someday"))
        due = None if someday else _parse_due(item.get("due_date"))
        due_time = item.get("due_time")
        if due_time is not None:
            due_time = str(due_time).strip() or None
        priority = int(item.get("priority") or 0)
        priority = max(0, min(3, priority))
        note = item.get("note")
        project_id = item.get("project_id")
        try:
            project_id = int(project_id) if project_id is not None else None
        except (TypeError, ValueError):
            project_id = None
        tid = add_task(
            title,
            due_date=due,
            due_time=due_time,
            priority=priority,
            note=str(note).strip() if note else None,
            project_id=project_id,
            tags=["assistant"] if not item.get("tags") else list(item.get("tags") or []),
        )
        row = get_task(tid, with_subtasks=False)
        if row:
            created.append(_task_brief(row))

    for raw_id in plan.get("complete_ids") or []:
        try:
            tid = int(raw_id)
        except (TypeError, ValueError):
            continue
        if not get_task(tid, with_subtasks=False):
            continue
        complete_task(tid)
        row = get_task(tid, with_subtasks=False)
        if row:
            completed.append(_task_brief(row))

    if plan.get("archive_done") is True:
        archived_n = archive_all_done()

    reply = str(plan.get("reply") or "").strip()
    if not reply:
        parts = []
        if matches:
            parts.append(f"Нашёл: {len(matches)}")
        if created:
            parts.append(f"Создал: {len(created)}")
        if completed:
            parts.append(f"Закрыл: {len(completed)}")
        if archived_n:
            parts.append(f"В архив: {archived_n}")
        reply = "; ".join(parts) or "Готово."

    return {
        "reply": reply,
        "matches": matches,
        "created": created,
        "completed": completed,
        "archived": archived_n,
        "plan": {
            "search": search_q,
            "create_count": len(created),
            "complete_ids": [c["id"] for c in completed],
            "archive_done": archived_n > 0,
        },
    }


async def run_assistant(message: str, *, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """LLM → JSON plan → execute tools. Offline fallback: local search/create heuristics."""
    msg = (message or "").strip()
    if not msg:
        return {
            "reply": "Напишите, что найти или создать.",
            "matches": [],
            "created": [],
            "completed": [],
            "archived": 0,
        }

    low = msg.lower().strip()

    # Local fast paths — работают даже если LLM тупит
    if re.search(r"архив|archive", low) and re.search(r"выполнен|истор|done|перенес", low):
        n = archive_all_done()
        return {
            "reply": f"В архив перенесено: {n}" if n else "Выполненных для архива нет.",
            "matches": [],
            "created": [],
            "completed": [],
            "archived": n,
            "model": "local",
        }

    if low.startswith(("найди ", "поиск ", "ищи ", "где ", "/find ")) or low in (
        "найди просроченные",
        "просроченные",
        "просрочено",
    ):
        q = re.sub(r"^(найди|поиск|ищи|где|/find)\s+", "", msg, flags=re.I).strip()
        if not q or "просроч" in q.lower() or low in ("просроченные", "просрочено"):
            today = _today().isoformat()
            matches = [
                _task_brief(t)
                for t in list_tasks(include_done=False)
                if t.get("due_date") and t["due_date"] < today
            ][:40]
            return {
                "reply": f"Просрочено: {len(matches)}" if matches else "Просроченных нет.",
                "matches": matches,
                "created": [],
                "completed": [],
                "archived": 0,
                "model": "local",
            }
        matches = search_tasks(q)
        return {
            "reply": f"Найдено: {len(matches)}" if matches else "Ничего не нашёл.",
            "matches": matches,
            "created": [],
            "completed": [],
            "archived": 0,
            "model": "local",
        }

    create_m = re.match(
        r"^(?:создай(?:те)?|добавь(?:те)?|новая задача|new)\s+(?:задач[уа]?\s+)?(.+)$",
        msg,
        flags=re.I,
    )
    if create_m:
        rest = create_m.group(1).strip()
        someday = bool(re.search(r"когда[- ]?нибудь|someday", rest, re.I))
        due = None
        title = rest
        if someday:
            title = re.sub(r"\bкогда[- ]?нибудь\b|\bsomeday\b", "", title, flags=re.I).strip(" ,.-")
        else:
            dm = re.search(
                r"\b(сегодня|завтра|послезавтра|\d{4}-\d{2}-\d{2})\b",
                title,
                flags=re.I,
            )
            if dm:
                due = _parse_due(dm.group(1))
                title = (title[: dm.start()] + title[dm.end() :]).strip(" ,.-")
        title = re.sub(r"\s+", " ", title).strip() or rest
        tid = add_task(title, due_date=due, tags=["assistant"])
        row = get_task(tid, with_subtasks=False)
        when = "без срока" if not due else due
        return {
            "reply": f"Создал: {title} ({when})",
            "matches": [],
            "created": [_task_brief(row)] if row else [],
            "completed": [],
            "archived": 0,
            "model": "local",
        }

    from tools.llm_client import chat_with_fallback

    user_block = msg
    if history:
        hist_lines = []
        for h in history[-6:]:
            role = h.get("role") or "user"
            hist_lines.append(f"{role}: {h.get('content','')[:400]}")
        user_block = "История:\n" + "\n".join(hist_lines) + "\n\nСообщение:\n" + msg

    model, content, meta = await chat_with_fallback(
        ASSISTANT_MODELS,
        user_block,
        system_prompt=_system_prompt(),
        temperature=0.2,
        max_tokens=1200,
        timeout=45.0,
    )
    if not (content or "").strip():
        if len(msg) <= 200 and "\n" not in msg and not msg.endswith("?"):
            tid = add_task(msg, tags=["assistant"])
            row = get_task(tid, with_subtasks=False)
            return {
                "reply": "Создал задачу (LLM недоступен).",
                "matches": [],
                "created": [_task_brief(row)] if row else [],
                "completed": [],
                "archived": 0,
                "model": "local-fallback",
                "error": (meta or {}).get("error"),
            }
        matches = search_tasks(msg)
        return {
            "reply": "LLM недоступен — показал поиск по тексту." if matches else "LLM недоступен.",
            "matches": matches,
            "created": [],
            "completed": [],
            "archived": 0,
            "model": "local-fallback",
            "error": (meta or {}).get("error"),
        }

    plan = _extract_json(content)
    result = _apply_plan(plan)
    result["model"] = model
    return result


def run_assistant_sync(message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run_assistant(message, history=history))
    raise RuntimeError("use_async_endpoint")
