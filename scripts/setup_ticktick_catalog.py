#!/usr/bin/env python3
"""Описания проектов TickTick + перенос шаблонов «Чек-листы» в таблицу checklists."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from planning_db import create_checklist, get_connection, init_db, list_checklists, list_tasks  # noqa: E402

from planning_ticktick_catalog import PROJECT_GUIDES, restore_ticktick_list_catalog

CHECKLIST_GUIDES: dict[str, str] = {
    "Поставить в нетбук твёрдый диск": (
        "Разовая техзадача; при желании перенести в Inbox или Проекты. "
        "Не шаблон — отдельный пункт."
    ),
    "Разбираем вещи": (
        "Дом / гардероб: алгоритм разбора одной вещи. "
        "Проект: быт. Запускать при уборке шкафа."
    ),
    "Чек-лист командировка": (
        "Служебная командировка (278 ВП и др.): перед выездом. "
        "Проект: служба. Связан с чек-листом отчёта по возвращении."
    ),
    "Чек-лист отчёт по командировке": (
        "После командировки: пакет документов для бухгалтерии/отдела. "
        "Проект: служба. Пункт 4 — отметки в 278 ВП."
    ),
    "Чек-лист по ведению конкретной работы": (
        "Контроль одного контракта/темы на предприятии. "
        "Проект: служба / ведомая тематика."
    ),
    "Чек-лист по службе в целом": (
        "Ежедневный/еженедельный ритуал офиса: почта, стол, летучий. "
        "Проект: служба."
    ),
    "Чек-лист сплав поход": (
        "Подготовка к сплаву с сыном и друзьями (цель «сплавы 2×/год»). "
        "Проект: семья / отдых."
    ),
    "Чек-лист уборка на работе и дома": (
        "Быстрая уборка рабочего места и дома. "
        "Проект: быт."
    ),
    "Чек-лист для наполнения рабочей папки по ведомой тематике": (
        "Собрать папку по контракту: ТЗ, договор, акты, ведомости. "
        "Проект: служба / архив темы."
    ),
}

ITEM_COMMENTS: dict[str, dict[str, str]] = {
    "Разбираем вещи": {
        "Для какого сезона вещь?": "Сезонность — оставить / убрать / сезонное хранилище.",
        "Нужно постирать?": "В корзину стирки, не обратно в шкаф.",
        "Можно носить на работе?": "Рабочий гардероб vs дом.",
        "Можно носить дома?": "Домашняя одежда.",
        "Нужно погладить?": "В очередь глажки.",
        "Нельзя носить совсем?": "Выброс / отдать.",
        "Можно положить на полку?": "Вернуть на место в шкафу.",
    },
}


def _parse_note_items(note: str | None) -> list[str]:
    if not note:
        return []
    items: list[str] = []
    for line in note.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[▫•\-]\s*", "", line)
        line = re.sub(r"^\d+\.\s*", "", line)
        if line:
            items.append(line)
    return items


def _item_title_with_comment(checklist_title: str, item: str) -> str:
    comments = ITEM_COMMENTS.get(checklist_title, {})
    for key, comment in comments.items():
        if key.lower() in item.lower() or item.lower().startswith(key.lower()):
            return f"{item} — {comment}"
    return item


def update_project_descriptions() -> int:
    init_db()
    conn = get_connection()
    updated = 0
    for title, desc in PROJECT_GUIDES.items():
        if title == "":
            continue
        cur = conn.execute(
            "UPDATE projects SET description = ?, updated_at = datetime('now') WHERE title = ?",
            (desc, title),
        )
        updated += cur.rowcount
    conn.commit()
    conn.close()
    return updated


def migrate_checklist_tasks() -> dict[str, int]:
    init_db()
    existing = {c["title"].lower(): c["id"] for c in list_checklists(status=None, limit=500)}
    created = skipped = 0
    tasks = list_tasks(project_id=_project_id("Чек-листы"), include_done=True, limit=100)
    for task in tasks:
        title = (task.get("title") or "").strip()
        if not title:
            continue
        if title.lower() in existing:
            skipped += 1
            continue
        guide = CHECKLIST_GUIDES.get(title, "Шаблон из TickTick; уточните назначение в описании.")
        raw_items = _parse_note_items(task.get("note"))
        if not raw_items and title == "Поставить в нетбук твёрдый диск":
            raw_items = [title]
        items = [_item_title_with_comment(title, it) for it in raw_items]
        if not items:
            items = ["(добавьте пункты вручную)"]
        desc = f"{guide}\n\nИсточник: TickTick / проект «Чек-листы». Задача #{task['id']}."
        create_checklist(
            title,
            description=desc,
            source="ticktick",
            tags=["чек-листы"],
            items=items,
        )
        existing[title.lower()] = 1
        created += 1
    return {"created": created, "skipped": skipped}


def _project_id(name: str) -> int | None:
    conn = get_connection()
    row = conn.execute("SELECT id FROM projects WHERE title = ?", (name,)).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def main() -> None:
    n = update_project_descriptions()
    cat = restore_ticktick_list_catalog(create_shells=True)
    mig = migrate_checklist_tasks()
    print(f"project descriptions updated: {n}")
    print(f"list catalog: {cat}")
    print(f"checklists created: {mig['created']}, skipped: {mig['skipped']}")
    print(f"total checklists: {len(list_checklists(status=None, limit=500))}")


if __name__ == "__main__":
    main()
