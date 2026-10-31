#!/usr/bin/env python3
"""
Seed карьерного плана B2B Lead Bot → Задачник (planning.db / PWA).

Канон (v1.1+):
  docs/career_12m_calendar_pauses_2026-10.md
  docs/career_curriculum_b2b_2026-10.md
  docs/career_strategy_synthesis_gemini_2026-10.md
  docs/career_tz_b2b_lead_bot_2026-10.md

  ./venv/bin/python scripts/seed_career_b2b_plan_2026.py
  ./venv/bin/python scripts/seed_career_b2b_plan_2026.py --force   # пересоздать чеклисты
  ./venv/bin/python scripts/seed_career_b2b_plan_2026.py --sync    # обновить вехи/ритуалы
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

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
GOAL_TITLE_LEGACY = (
    "Карьера · 350к белый IT (уход 6–12 мес.)",
)
PROJECT_TITLE = "Карьера · B2B Lead Bot / выход"
CANON = "docs/career_curriculum_b2b_2026-10.md"
CANON_CAL = "docs/career_12m_calendar_pauses_2026-10.md"
CANON_TZ = "docs/career_tz_b2b_lead_bot_2026-10.md"

TAGS = ["career", "b2b-bot", "2026", "exit"]

# Все agent_ref, которыми владеет этот seed (старые + новые) — для --force archive
MANAGED_REFS = (
    # legacy
    "career-b2b-pipeline",
    "career-b2b-phase-0",
    "career-b2b-phase-1",
    "career-b2b-week-1",
    "career-b2b-week-2",
    "career-b2b-week-3",
    "career-b2b-week-4",
    "career-b2b-week-5",
    "career-b2b-phase-2",
    "career-b2b-phase-2b",
    "career-b2b-phase-3",
    "career-b2b-phase-4",
    "career-b2b-phase-5",
    "career-b2b-en",
    "career-b2b-weekly-review",
    "career-b2b-ready-exit",
    # v1.1
    "career-b2b-phase-s0",
    "career-b2b-phase-s1",
    "career-b2b-phase-s2",
    "career-b2b-phase-s3",
    "career-b2b-phase-s4",
    "career-b2b-phase-s5",
    "career-b2b-phase-s6",
    "career-b2b-phase-s7",
    "career-b2b-mod-0",
    "career-b2b-mod-1",
    "career-b2b-mod-2",
    "career-b2b-mod-3",
    "career-b2b-mod-4",
    "career-b2b-mod-5",
    "career-b2b-mod-6",
    "career-b2b-mod-7",
    "career-b2b-mod-8",
    "career-b2b-mod-9",
    "career-b2b-mod-10",
    # v2 Личный Практикум (Gemini)
    "career-b2b-sem1-onboard",
    "career-b2b-sem1-mod1",
    "career-b2b-sem1-mod2",
    "career-b2b-sem1-mod3",
    "career-b2b-sem1-mod4",
    "career-b2b-daily-report",
    "career-b2b-pause-protocol",
    "career-b2b-media-parallel",
)


def _find_goal_id(*titles: str) -> int | None:
    init_db()
    conn = get_connection()
    for title in titles:
        row = conn.execute("SELECT id FROM goals WHERE title = ?", (title,)).fetchone()
        if row:
            conn.close()
            return int(row["id"])
    conn.close()
    return None


def _update_goal(goal_id: int, title: str, description: str, target_date: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE goals SET title=?, description=?, target_date=?, updated_at=datetime('now') WHERE id=?",
        (title, description, target_date, goal_id),
    )
    conn.commit()
    conn.close()


def _find_project_id(title: str) -> int | None:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT id FROM projects WHERE title = ?", (title,)).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def _upsert_project(title: str, goal_id: int | None, description: str) -> int:
    pid = _find_project_id(title)
    if pid is None:
        pid = add_project(
            title,
            goal_id=goal_id,
            description=description,
            folder_name="Карьера",
            sort_order=50,
        )
        print(f"  created project: {title} id={pid}")
        return pid
    conn = get_connection()
    conn.execute(
        """
        UPDATE projects
        SET description=?, goal_id=?, folder_name=?, updated_at=datetime('now')
        WHERE id=?
        """,
        (description, goal_id, "Карьера", pid),
    )
    conn.commit()
    conn.close()
    print(f"  updated project: {title} id={pid}")
    return pid


def _archive_checklist(cid: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE checklists SET status='archived', updated_at=datetime('now') WHERE id=?",
        (cid,),
    )
    conn.commit()
    conn.close()


def _ensure_checklist(
    agent_ref: str,
    title: str,
    description: str,
    items: list[str],
    *,
    tags: list[str] | None = None,
    force: bool = False,
) -> int:
    existing = find_checklist_by_ref(agent_ref)
    if existing and not force:
        print(f"  checklist exists: {agent_ref} id={existing['id']}")
        return int(existing["id"])
    if existing and force:
        _archive_checklist(int(existing["id"]))
        print(f"  archived: {agent_ref} id={existing['id']}")
    cid = create_checklist(
        title,
        description=description,
        source=SOURCE_AGENT,
        agent_ref=agent_ref,
        tags=tags or TAGS,
        items=items,
    )
    print(f"  created checklist: {agent_ref} id={cid} ({len(items)} items)")
    return cid


def _task_by_source(source: str) -> int | None:
    init_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM tasks WHERE obsidian_source = ? LIMIT 1", (source,)
    ).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def _milestone_source(due_date: str, title: str) -> str:
    slug = re.sub(r"[^\w]+", "-", title.lower(), flags=re.UNICODE)[:48].strip("-")
    return f"career-b2b:milestone:{due_date}:{slug}"


def _ensure_milestone(
    title: str,
    due_date: str,
    project_id: int | None,
    goal_id: int | None,
    note: str,
    priority: int,
    *,
    sync: bool = False,
    tags: list[str] | None = None,
    repeat_rule: dict | None = None,
    source: str | None = None,
) -> None:
    source = source or _milestone_source(due_date, title)
    existing_id = _task_by_source(source)
    task_tags = tags or ["career", "веха", "b2b-bot"]
    if existing_id:
        if sync:
            kwargs = dict(
                title=title,
                note=note or None,
                due_date=due_date,
                project_id=project_id,
                goal_id=goal_id,
                priority=priority,
                tags=task_tags,
            )
            if repeat_rule is not None:
                kwargs["repeat_rule"] = repeat_rule
            update_task(existing_id, **kwargs)
            print(f"  milestone synced: {due_date} {title[:48]}")
        else:
            print(f"  milestone exists: {due_date} {title[:48]}")
        return
    tid = add_task(
        title,
        project_id=project_id,
        goal_id=goal_id,
        due_date=due_date,
        priority=priority,
        note=note or None,
        tags=task_tags,
        obsidian_source=source,
        repeat_rule=repeat_rule,
    )
    print(f"  milestone id={tid}: {due_date} {title[:50]}")


# --- пайплайн (взвешенный %) ---

PIPELINE_ITEMS = [
    "[5%] КТ-0 · Онбординг + tracker стендапы (docs/tracker)",
    "[15%] Sem1 M1 · Python+Git · To-Do CLI (нед. 1–4)",
    "[15%] Sem1 M2 · Aiogram+FSM · echo+анкета (нед. 5–8)",
    "[15%] Sem1 M3 / КТ-1 · SQL+ORM · память в БД (нед. 9–12)",
    "[20%] Sem1 M4 / КТ-2 · Диплом Lead Bot Docker+Sheets+VPS (нед. 13–16)",
    "[10%] Sem2 · Alembic/админ + КТ-3 рынок (кейсы/CustDev)",
    "[10%] КТ-4 · go/no-go (подушка, юрконтур, ≥5 касаний)",
    "[10%] D-day · уход 12–24 мес + белый контур",
]

PHASE_S0 = [
    "Режим: deep work 20–24 ч/нед; семья/спорт ≥4 ч/день; работа ≤3 ч",
    "Burn ₽/мес + подушка + черновой D-day (квартал)",
    "Метрика обоих сайтов ИЛИ блокер YANDEX_METRIKA_ID",
    "Репо b2b_lead_bot + docs/tracker/DAILY_STANDUP.md открыт",
    "python≥3.11, docker, git OK",
    "Anki + правило ментора (.cursor/rules/career-practicum-mentor.mdc)",
    f"Прочитан Личный Практикум: {CANON}",
]

PHASE_S1 = [
    "Sem1 M1: Stepik 58852 идёт; To-Do CLI add/list/done",
    "Git: feature/* + ≥5 коммитов",
    "Критерий M1: словарь/функции объяснимы голосом",
]

PHASE_S2 = [
    "Sem1 M2: Mastergroosha + echo-бот",
    "FSM-анкета → консоль; /cancel",
    "polling vs webhook — 1 абзац",
]

PHASE_S3 = [
    "Sem1 M3: SQL тренажёр + SQLite leads",
    "SQLAlchemy model; рестарт не убивает данные",
    "КТ-1: схема leads объяснима голосом",
    "Sem1 M4 диплом: compose + Sheets + README + VPS",
    "КТ-2: демо с нуля / Loom",
]

PHASE_S4 = [
    "Alembic: миграция status без потери данных",
    "Логи ERROR при сбоях",
    "Кнопки статуса лида для админа",
    "Прогон compose на VPS через git pull (руками)",
]

PHASE_S5 = [
    "Выбран один путь: Google Sheets ИЛИ CRM webhook",
    "integrations/ + секреты в .env",
    "try/except: лид в Postgres при падении API; админу алерт",
    "Демо-скрин в README",
]

PHASE_S6 = [
    "2 кейса в README (бот + интеграция)",
    "Список 15 агентств + шаблон письма (черновик)",
    "5 CustDev только боли — без цены/оффера",
    "EN pitch 90 сек",
    "One-pager + резюме Python/Telegram bots",
    "КТ-3 закрыт",
]

PHASE_S7 = [
    "Подушка не проедена",
    "≥5 живых касаний рынка",
    "Белый контур после ухода ясен (ИП/самозанятость — с юристом)",
    "КТ-4 go/no-go = да",
    "Дата увольнения внутри 12–24 мес от старта",
]

PHASE_POST = [
    "Дни 1–30: цель 150–200к (субподряд C)",
    "Дни 31–60: 200–250к",
    "Дни 61–90: путь к 300–350к",
    "Airflow/dbt — только по сигналу рынка",
]

# --- Семестр 1 · Личный Практикум (Gemini) ---

SEM1_ONBOARD = [
    "Режим суток: работа≤3 · семья≥4 · deep work в бюджете 20–24/нед",
    "Burn + подушка + черновой D-day",
    "Репо b2b_lead_bot + sandbox/",
    "Открыт docs/tracker/DAILY_STANDUP.md — первая запись",
    "Ментор: .cursor/rules/career-practicum-mentor.mdc",
    f"Курс: {CANON}",
]

SEM1_MOD1 = [
    "Недели 1–4 · Python + Git",
    "Stepik Поколение Python: https://stepik.org/course/58852/",
    "Tutorial: https://docs.python.org/3/tutorial/",
    "Git basics: https://git-scm.com/book/ru/v2",
    "Проект: sandbox To-Do CLI (txt/json) add/list/done",
    "≥5 коммитов; ветка feature/*",
    "Критерий: объясняю list/dict/функцию голосом",
]

SEM1_MOD2 = [
    "Недели 5–8 · Aiogram + async + FSM",
    "Mastergroosha: https://mastergroosha.github.io/aiogram-3-guide/",
    "Quickstart: https://mastergroosha.github.io/aiogram-3-guide/quickstart/",
    "FSM глава: https://mastergroosha.github.io/aiogram-3-guide/fsm/",
    "Docs aiogram: https://docs.aiogram.dev/en/latest/",
    "Проект: echo-бот + анкета (имя/телефон/запрос) → консоль",
    "/cancel; токен в .env",
    "Критерий: polling vs webhook одним абзацем",
]

SEM1_MOD3 = [
    "Недели 9–12 · SQL + SQLAlchemy → КТ-1",
    "SQL Stepik: https://stepik.org/course/63054/",
    "SQL Academy: https://sql-academy.org/",
    "SQLAlchemy quickstart: https://docs.sqlalchemy.org/en/20/orm/quickstart.html",
    "YouTube: SQLAlchemy 2.0 (напр. Артём Шумейко) → сразу практика",
    "Проект: анкета пишет в SQLite, затем Postgres",
    "Рестарт не убивает leads",
    "КТ-1: схема leads объяснима",
]

SEM1_MOD4 = [
    "Недели 13–16 · Диплом Lead Bot → КТ-2",
    "Docker Get Started: https://docs.docker.com/get-started/",
    "Compose: https://docs.docker.com/compose/compose-file/",
    "Stepik Docker для начинающих (поиск) + доки",
    "Sheets concepts: https://developers.google.com/sheets/api/guides/concepts",
    "Sheets quickstart: https://developers.google.com/sheets/api/quickstart/python",
    "logging: https://docs.python.org/3/howto/logging.html",
    "Диплом: Docker + Postgres + Sheet + логи + VPS (руками)",
    "README ≤5 команд; демо 5 мин = КТ-2",
]

DAILY_REPORT = [
    "Режим: HOME / PAUSE / RECOVERY · оценка фокуса 1–10",
    "Семья/спорт ≥4 ч: да/нет · работа __ ч · deep work __ ч",
    "Блок А · Учёба/B2B __ ч — что сделал (Stepik/код/коммит)",
    "Блок А · Сложности (что не понял → вопрос ментору)",
    "Блок Б · Медиа/Пенсия __ ч — сделано / перенос",
    "Блок В · Где Пар/инфра __ ч",
    "English __ мин",
    "План на завтра: 1) B2B 2) медиа 3) семья без телефона",
    "Запись скопирована в docs/tracker/DAILY_STANDUP.md",
]

WEEKLY_REVIEW = [
    "ВОСКРЕСЕНЬЕ · спринт-ревью (docs/tracker/WEEKLY_SPRINT.md)",
    "Deep work факт / 20–24 · режим недели HOME/PAUSE",
    "1. Что сделано / что провалено",
    "2. Темы кода, которые ещё не понимаю → вопросы ментору на пн",
    "3. Одна главная цель на следующие 7 дней",
    "% пайплайна · модуль Sem1 · ближайшая КТ",
    "Семья/спорт: дни <4 ч?",
    f"Канон: {CANON} · {CANON_CAL}",
]

PAUSE_PROTOCOL = [
    "За 7 дней: коммит/пуш + NOTES «на чём остановился»",
    "Журнал пауз в career_12m_calendar §5 заполнен",
    "Пакет на слабый ПК: Stepik неделя + 2–3 главы/сценария + Anki",
    "Запрет: деплой, Flint/VPN, 4K, Ollama, правка прод-VPS",
    "На месте: B2B учёба 8–9 ч · EN 3 · текст Пенсии 2–3 · Где Пар ≤1",
    "КТ незакрытые сдвинуты на длину PAUSE (формула календаря)",
    "После: RECOVERY 1 нед (−30%, без новых идей)",
]

EN_ITEMS = [
    "Ежедневно 30 мин: docs текущего модуля + Anki",
    "1×/нед: голосовое EN «что сделал»",
    "КТ-1 зона: термины FSM/SQL в Anki",
    "КТ-2: EN-пересказ README бота (15–20 предложений)",
    "КТ-3: 90-сек pitch на EN",
    "К поздней КТ: ≥300 карточек Anki",
    "Anki: https://apps.ankiweb.net/",
]

MEDIA_PARALLEL = [
    "Пенсия 6–7 ч/нед: книга / сценарий / ролик (прокси Resolve)",
    "Где Пар 2–3 ч/нед: Метрика + воронка; без парсер-свалки",
    "Автоканалы ≤1 ч/нед: только review автопоста",
    "Метрика: docs/metrika_goals_setup.md",
    "Полка (Снегири и т.п.) — не открывать до D-day+90 при КТ-4=да",
]

READY_EXIT = [
    "2 рабочих артефакта на GitHub (бот + интеграция)",
    "Могу объяснить код голосом",
    "≥5 живых касаний рынка",
    "Подушка не проедена",
    "Белый контур после ухода ясен",
    "КТ-4 = да",
]

MILESTONES: list[tuple[str, str, str, int]] = [
    ("КТ-0 · онбординг + tracker", "2026-10-31", "sem1-onboard", 3),
    ("Sem1 M1 старт · Stepik + To-Do", "2026-11-07", "недели 1–4", 2),
    ("Sem1 M1 done · To-Do CLI", "2026-11-30", "критерий модуля 1", 2),
    ("Sem1 M2 · echo+FSM анкета", "2026-12-28", "Mastergroosha; недели 5–8", 2),
    ("КТ-1 · БД память (конец M3)", "2027-01-21", "недели 9–12", 3),
    ("Sem1 M4 диплом старт", "2027-02-01", "недели 13–16", 2),
    ("КТ-2 · Lead Bot диплом", "2027-05-21", "Docker+Sheets+VPS", 3),
    ("Sem2 · Alembic/админ", "2027-07-15", "после диплома", 2),
    ("КТ-3 · рынок / кейсы", "2027-08-21", "CustDev без продажи", 3),
    ("КТ-4 · go/no-go", "2027-09-21", "ready-exit", 3),
    ("D-day · черновой уход (+12 мес)", "2027-10-22", "PAUSE сдвигает; край +24 мес", 3),
    ("Окно ухода · край +24 мес", "2028-04-22", "буфер", 2),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed career B2B plan → Задачник")
    parser.add_argument("--force", action="store_true", help="пересоздать чеклисты")
    parser.add_argument("--sync", action="store_true", help="обновить вехи/ритуалы")
    args = parser.parse_args()

    skip_checklists = False
    if not args.force and find_checklist_by_ref("career-b2b-pipeline"):
        # Detect stale pipeline (old MVP-nov wording) → suggest --force
        print("Чеклисты career уже есть — пропуск создания (добавь --force).")
        print("Проект и вехи обновляются идемпотентно; --sync обновит вехи.\n")
        skip_checklists = True

    goal_desc = (
        f"Белый выход на ~350к после ухода. Горизонт 12–24 мес. "
        f"Песочница → MVP → рынок. Deep work 20–24 ч/нед; семья ≥4 ч/день; работа ≤3 ч. "
        f"Учёба: {CANON}. Паузы: {CANON_CAL}. ТЗ продукта: {CANON_TZ}."
    )
    goal_id = _find_goal_id(GOAL_TITLE, *GOAL_TITLE_LEGACY)
    if goal_id is None:
        goal_id = add_goal(GOAL_TITLE, description=goal_desc, target_date="2027-10-22")
        print(f"created goal id={goal_id}")
    else:
        _update_goal(goal_id, GOAL_TITLE, goal_desc, "2027-10-22")
        print(f"updated goal id={goal_id}")

    print("\n=== Проект ===")
    project_id = _upsert_project(
        PROJECT_TITLE,
        goal_id,
        f"Пайплайн + курс (модули M0–M10) + дневной отчёт + PAUSE. "
        f"{CANON} · {CANON_CAL}. Чеклисты: поиск «Карьера ·».",
    )

    if not skip_checklists:
        print("\n=== Pipeline % ===")
        _ensure_checklist(
            "career-b2b-pipeline",
            "Карьера · Pipeline итоговый %",
            f"Взвешенный прогресс. Канон: {CANON_CAL}",
            PIPELINE_ITEMS,
            tags=TAGS + ["pipeline", "weighted"],
            force=args.force,
        )

        print("\n=== Фазы (S0–S7 + post) ===")
        for ref, title, desc, items in (
            ("career-b2b-phase-s0", "Карьера · Фаза S0 · Онбординг", "КТ-0 · tracker", PHASE_S0),
            ("career-b2b-phase-s1", "Карьера · Фаза S1 · Sem1 Python/Git", "модуль 1", PHASE_S1),
            ("career-b2b-phase-s2", "Карьера · Фаза S2 · Sem1 Aiogram/FSM", "модуль 2", PHASE_S2),
            ("career-b2b-phase-s3", "Карьера · Фаза S3 · Sem1 SQL+диплом → КТ-1/2", "модули 3–4", PHASE_S3),
            ("career-b2b-phase-s4", "Карьера · Фаза S4 · Alembic/VPS (Sem2)", "после диплома", PHASE_S4),
            ("career-b2b-phase-s5", "Карьера · Фаза S5 · Sheets polish", "если не в дипломе", PHASE_S5),
            ("career-b2b-phase-s6", "Карьера · Фаза S6 · Рынок → КТ-3", "Sem2", PHASE_S6),
            ("career-b2b-phase-s7", "Карьера · Фаза S7 · Go/no-go → КТ-4", "pre-exit", PHASE_S7),
            ("career-b2b-phase-5", "Карьера · Фаза · 90 дней после ухода", "150–200к → 350к", PHASE_POST),
        ):
            _ensure_checklist(ref, title, desc, items, force=args.force)

        print("\n=== Семестр 1 · модули Личного Практикума ===")
        for ref, title, items in (
            ("career-b2b-sem1-onboard", "Карьера · Sem1 · Онбординг", SEM1_ONBOARD),
            ("career-b2b-sem1-mod1", "Карьера · Sem1 · Модуль 1 · Python+Git (нед.1–4)", SEM1_MOD1),
            ("career-b2b-sem1-mod2", "Карьера · Sem1 · Модуль 2 · Aiogram+FSM (нед.5–8)", SEM1_MOD2),
            ("career-b2b-sem1-mod3", "Карьера · Sem1 · Модуль 3 · SQL+ORM (нед.9–12)", SEM1_MOD3),
            ("career-b2b-sem1-mod4", "Карьера · Sem1 · Модуль 4 · Диплом Lead Bot (нед.13–16)", SEM1_MOD4),
        ):
            _ensure_checklist(
                ref,
                title,
                f"Личный Практикум: {CANON}",
                items,
                tags=TAGS + ["curriculum", "semester1"],
                force=args.force,
            )

        if args.force:
            for legacy_mod in (
                "career-b2b-mod-0",
                "career-b2b-mod-1",
                "career-b2b-mod-2",
                "career-b2b-mod-3",
                "career-b2b-mod-4",
                "career-b2b-mod-5",
                "career-b2b-mod-6",
                "career-b2b-mod-7",
                "career-b2b-mod-8",
                "career-b2b-mod-9",
                "career-b2b-mod-10",
            ):
                ex = find_checklist_by_ref(legacy_mod)
                if ex and ex.get("status") != "archived":
                    _archive_checklist(int(ex["id"]))
                    print(f"  archived legacy module: {legacy_mod}")

        print("\n=== Ритуалы / параллели ===")
        _ensure_checklist(
            "career-b2b-daily-report",
            "Карьера · Ежедневный стендап (Daily Standup)",
            "docs/tracker/DAILY_STANDUP.md · ~10 мин вечером · repeat daily",
            DAILY_REPORT,
            tags=TAGS + ["ritual", "daily"],
            force=args.force,
        )
        _ensure_checklist(
            "career-b2b-weekly-review",
            "Карьера · Воскресный спринт-ревью",
            "docs/tracker/WEEKLY_SPRINT.md · 3 вопроса",
            WEEKLY_REVIEW,
            tags=TAGS + ["ritual", "weekly"],
            force=args.force,
        )
        _ensure_checklist(
            "career-b2b-pause-protocol",
            "Карьера · Протокол PAUSE (отъезд)",
            CANON_CAL,
            PAUSE_PROTOCOL,
            tags=TAGS + ["ritual", "pause"],
            force=args.force,
        )
        _ensure_checklist(
            "career-b2b-en",
            "Карьера · English (параллельно)",
            "30 мин/день",
            EN_ITEMS,
            tags=TAGS + ["english"],
            force=args.force,
        )
        _ensure_checklist(
            "career-b2b-media-parallel",
            "Карьера · Медиа-микротрек (Пенсия/Где Пар)",
            "Не вместо B2B; доли из календаря",
            MEDIA_PARALLEL,
            tags=TAGS + ["media"],
            force=args.force,
        )
        _ensure_checklist(
            "career-b2b-ready-exit",
            "Карьера · Готовность к уходу (все галочки)",
            "Не увольняться, пока не закрыто",
            READY_EXIT,
            tags=TAGS + ["gate"],
            force=args.force,
        )

        # Archive legacy week/phase checklists if force (already archived via ref recreate);
        # if force, also archive any leftover legacy refs not recreated
        if args.force:
            for legacy in (
                "career-b2b-phase-0",
                "career-b2b-phase-1",
                "career-b2b-phase-2",
                "career-b2b-phase-2b",
                "career-b2b-phase-3",
                "career-b2b-phase-4",
                "career-b2b-week-1",
                "career-b2b-week-2",
                "career-b2b-week-3",
                "career-b2b-week-4",
                "career-b2b-week-5",
            ):
                ex = find_checklist_by_ref(legacy)
                if ex and ex.get("status") != "archived":
                    _archive_checklist(int(ex["id"]))
                    print(f"  archived legacy: {legacy}")

    print("\n=== Вехи (календарь) ===")
    for title, due, note, prio in MILESTONES:
        _ensure_milestone(
            title,
            due,
            project_id,
            goal_id,
            f"{note}\n{CANON}\n{CANON_CAL}",
            prio,
            sync=args.sync,
        )

    print("\n=== Ритуалы · repeat ===")
    _ensure_milestone(
        "Карьера · Daily Standup (стендап)",
        "2026-10-22",
        project_id,
        goal_id,
        "Чеклист стендапа + docs/tracker/DAILY_STANDUP.md (~10 мин)",
        2,
        sync=args.sync,
        tags=["career", "ritual", "daily"],
        repeat_rule={"freq": "daily", "interval": 1},
        source="career-b2b:ritual:daily-report",
    )
    _ensure_milestone(
        "Карьера · Sprint review (воскресенье)",
        "2026-10-26",
        project_id,
        goal_id,
        "Чеклист воскресного ревью + docs/tracker/WEEKLY_SPRINT.md",
        2,
        sync=args.sync,
        tags=["career", "ritual", "weekly"],
        repeat_rule={"freq": "weekly", "interval": 1, "byweekday": ["sun"]},
        source="career-b2b:ritual:weekly-review",
    )

    print(
        "\nГотово.\n"
        "  Пайплайн → вкладка «Карьера · B2B»\n"
        "  Чеклисты → «Карьера · Модуль …» / Фаза S… / Ежедневный отчёт\n"
        "  Календарь → КТ + daily/weekly rituals\n"
        f"  Курс: {CANON}\n"
        "Обновить UI-вкладки: static/planning/finance_model_content.js (career).\n"
        "Повтор: --force (чеклисты) и/или --sync (вехи)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
