#!/usr/bin/env python3
"""
Личный Практикум LMS → planning.db (с нуля, недельные уроки).

UX-якорь: Codecademy Career Path (Baymard top UX) —
  path → modules/weeks → lesson steps, прогресс по каждому уроку, Continue.
Структура контента: Яндекс Практикум / Gemini Личный Практикум
  (30% теория / 70% практика, модули Python→Aiogram→SQL→диплом).

  ./venv/bin/python scripts/seed_practicum_lms_2026.py --force
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from go_learn import COURSE_ORDER  # noqa: E402
from planning_db import (  # noqa: E402
    SOURCE_AGENT,
    add_goal,
    add_project,
    add_task,
    create_checklist,
    find_checklist_by_ref,
    get_connection,
    init_db,
    update_task,
)

GOAL_TITLE = "Карьера · 350к белый IT (уход 12–24 мес.)"
PROJECT_TITLE = "Карьера · B2B Lead Bot / выход"
CANON = "docs/career_curriculum_b2b_2026-10.md"
TAGS = ["career", "b2b-bot", "lms", "2026"]

# Недельные шаги (Codecademy: 5–7 упражнений на урок)
LESSONS: dict[str, list[str]] = {
    "lms-sem1-w00": [
        "Режим: работа ≤3 ч · семья/спорт ≥4 ч · deep work 20–24 ч/нед",
        "Burn ₽/мес + подушка + черновой D-day (квартал)",
        "Репо b2b_lead_bot + папка sandbox/",
        "Открыт docs/tracker/DAILY_STANDUP.md — первая запись сегодня",
        "Ментор: .cursor/rules/career-practicum-mentor.mdc (не просить готовый код)",
        f"Прочитан силлабус: {CANON}",
        "В Практикуме (/go-learn/) открыта Неделя 1",
    ],
    "lms-sem1-w01": [
        "Stepik 58852: установка Python + первые задачи (типы)",
        "Tutorial docs.python.org: §1–3 (прогон в REPL)",
        "Написать 5 if/elif примеров без копипасты",
        "Anki: 10 карточек типов/операторов",
        "Стендап вечером (чеклист Daily Standup)",
    ],
    "lms-sem1-w02": [
        "Stepik: циклы for/while + функции (нед. блок)",
        "Написать 3 функции со списками (map руками)",
        "Разобрать list vs tuple голосом ≤2 мин",
        "Git init в sandbox/todo_cli (если ещё нет)",
        "Стендап + EN 30 мин",
    ],
    "lms-sem1-w03": [
        "Словари: 10 задач Stepik / своих",
        "To-Do CLI: add / list / done в .json",
        "Обработка ошибок: файл не найден",
        "Критерий черновик: объясняю dict без шпаргалки",
        "Стендап",
    ],
    "lms-sem1-w04": [
        "Pro Git Basics: commit / branch / merge",
        "≥5 осмысленных коммитов на To-Do",
        "Ветка feature/* → merge в main",
        "КРИТЕРИЙ M1: To-Do работает + голосом list/dict/функция",
        "Sprint review (вс) · WEEKLY_SPRINT.md",
    ],
    "lms-sem1-w05": [
        "Mastergroosha Quickstart целиком",
        "venv + aiogram 3 в sandbox/echo_bot",
        "Бот отвечает на /start",
        "Токен только в .env (не в git)",
        "Стендап",
    ],
    "lms-sem1-w06": [
        "Echo: любой текст → echo",
        "Хендлеры: команды vs текст",
        "Логирование входящих (print/logging)",
        "polling: что это, одним абзацем в NOTES.md",
        "Стендап",
    ],
    "lms-sem1-w07": [
        "FSM глава Mastergroosha",
        "Анкета: имя → телефон → запрос",
        "Состояния и MemoryStorage",
        "Вывод анкеты в консоль/лог",
        "Стендап",
    ],
    "lms-sem1-w08": [
        "/cancel сбрасывает FSM",
        "README: как запустить бота (3 команды)",
        "КРИТЕРИЙ M2: polling vs webhook · /cancel работает",
        "EN: пересказ «что делает бот» 60 сек",
        "Sprint review",
    ],
    "lms-sem1-w09": [
        "Stepik SQL 63054: SELECT / WHERE / ORDER",
        "SQL Academy: 15 задач",
        "Нарисовать схему leads на бумаге",
        "Стендап",
    ],
    "lms-sem1-w10": [
        "SQLite файл leads.db",
        "INSERT из «анкеты» (скрипт или бот)",
        "SELECT всех лидов",
        "Рестарт скрипта — данные на месте",
        "Стендап",
    ],
    "lms-sem1-w11": [
        "SQLAlchemy 2.0 ORM Quick Start",
        "Model Lead (id, name, phone, request, created_at)",
        "Бот пишет Lead через ORM",
        "Миграция мысли: зачем Alembic (NOTES)",
        "Стендап",
    ],
    "lms-sem1-w12": [
        "Тот же schema на Postgres локально (docker optional)",
        "КРИТЕРИЙ = КТ-1: рестарт не убивает; схема голосом",
        "Anki: FSM + SQL термины",
        "Sprint review · % пайплайна",
    ],
    "lms-sem1-w13": [
        "Docker Get Started (офиц.)",
        "Dockerfile для бота",
        "Сборка и run локально",
        "Стендап",
    ],
    "lms-sem1-w14": [
        "compose: bot + postgres",
        "ENV через .env / compose",
        "Данные в volume",
        "Стендап",
    ],
    "lms-sem1-w15": [
        "Google Sheets API concepts + quickstart Python",
        "Новый лид → строка в Sheet (или mock)",
        "logging ERROR при сбоях",
        "Стендап",
    ],
    "lms-sem1-w16": [
        "README ≤5 команд с нуля",
        "Деплой на VPS руками (git pull + compose)",
        "Демо 5 мин / Loom = КТ-2",
        "EN пересказ README 15 предложений",
        "Sprint review · готовность Sem2",
    ],
}

MILESTONES = [
    ("КТ-0 · онбординг", "2026-10-26", 3),
    ("M1 done · To-Do CLI", "2026-11-23", 2),
    ("M2 done · FSM бот", "2026-12-21", 2),
    ("КТ-1 · БД память", "2027-01-18", 3),
    ("КТ-2 · Lead Bot диплом", "2027-02-15", 3),
]


def _archive(cid: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE checklists SET status='archived', updated_at=datetime('now') WHERE id=?",
        (cid,),
    )
    conn.commit()
    conn.close()


def _ensure_cl(ref: str, title: str, items: list[str], *, force: bool, desc: str) -> int:
    ex = find_checklist_by_ref(ref)
    if ex and not force:
        print(f"  exists {ref} id={ex['id']}")
        return int(ex["id"])
    if ex and force:
        _archive(int(ex["id"]))
        print(f"  archived {ref}")
    cid = create_checklist(
        title,
        description=desc,
        source=SOURCE_AGENT,
        agent_ref=ref,
        tags=TAGS + ["curriculum", "semester1", "week"],
        items=items,
    )
    print(f"  created {ref} id={cid} ({len(items)} steps)")
    return cid


def _goal() -> int:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT id FROM goals WHERE title = ?", (GOAL_TITLE,)).fetchone()
    if row:
        gid = int(row["id"])
        conn.close()
        return gid
    conn.close()
    return add_goal(
        GOAL_TITLE,
        description=f"LMS Practikum. {CANON}",
        target_date="2027-10-22",
    )


def _project(goal_id: int) -> int:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT id FROM projects WHERE title = ?", (PROJECT_TITLE,)).fetchone()
    if row:
        pid = int(row["id"])
        conn.execute(
            "UPDATE projects SET goal_id=?, folder_name=?, updated_at=datetime('now') WHERE id=?",
            (goal_id, "Карьера", pid),
        )
        conn.commit()
        conn.close()
        return pid
    conn.close()
    return add_project(
        PROJECT_TITLE,
        goal_id=goal_id,
        description="LMS /go-learn/ + пайплайн",
        folder_name="Карьера",
        sort_order=50,
    )


def _milestone(title: str, due: str, project_id: int, goal_id: int, prio: int) -> None:
    src = f"lms-sem1:milestone:{due}"
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM tasks WHERE obsidian_source = ? LIMIT 1", (src,)
    ).fetchone()
    conn.close()
    if row:
        update_task(
            int(row["id"]),
            title=title,
            due_date=due,
            project_id=project_id,
            goal_id=goal_id,
            priority=prio,
            tags=["career", "веха", "lms"],
        )
        print(f"  milestone sync {due} {title}")
        return
    add_task(
        title,
        project_id=project_id,
        goal_id=goal_id,
        due_date=due,
        priority=prio,
        tags=["career", "веха", "lms"],
        obsidian_source=src,
        note=CANON,
    )
    print(f"  milestone new {due} {title}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    print("=== Goal / project ===")
    gid = _goal()
    pid = _project(gid)
    print(f"goal={gid} project={pid}")

    print("\n=== Weekly lessons (LMS) ===")
    for ref, title, window, est in COURSE_ORDER:
        items = LESSONS.get(ref)
        if not items:
            print(f"  SKIP no items: {ref}")
            continue
        _ensure_cl(
            ref,
            f"Практикум · {title}",
            items,
            force=args.force,
            desc=f"{window} · {est} · {CANON}",
        )

    # Сводка-пайплайн для вкладки Карьера
    print("\n=== Pipeline summary ===")
    _ensure_cl(
        "career-b2b-pipeline",
        "Карьера · Pipeline итоговый %",
        [
            "[5%] КТ-0 · Онбординг",
            "[15%] M1 · Python+Git · To-Do",
            "[15%] M2 · Aiogram+FSM",
            "[15%] M3 / КТ-1 · SQL+ORM",
            "[20%] M4 / КТ-2 · Диплом Lead Bot",
            "[10%] Sem2 · рынок",
            "[10%] КТ-4 · go/no-go",
            "[10%] D-day",
        ],
        force=args.force,
        desc="Взвешенный % · зеркало /go-learn/",
    )

    print("\n=== Milestones ===")
    for title, due, prio in MILESTONES:
        _milestone(title, due, pid, gid, prio)

    print(
        "\nГотово. Открой https://neverretire.ru/go-learn/\n"
        "Канон: " + CANON
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
