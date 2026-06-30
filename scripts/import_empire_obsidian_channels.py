#!/usr/bin/env python3
"""Импорт Pension + Gdepar + Финансы из Obsidian-сценариев в Empire Tasks.

Проекты Empire содержат ТОЛЬКО задачи с obsidian_source=empire:obsidian:*.
TickTick-задачи (ticktick:*) никогда не переносятся в эти проекты автоматически.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from planning_db import (  # noqa: E402
    add_task,
    create_checklist,
    get_connection,
    init_db,
    list_checklists,
    update_task,
    update_task_status,
)

SCENARIOS = ROOT / "data/obsidian_vault/Empire/_scenarios/checklists"

AUTOPOST_NOTE = (
    "Автопост (июнь 2026): все каналы — garden, gdepar, stern, lenin, pension — "
    "в едином пайплайне data/auto_publish.json · docs/empire_autopost_strategy_2026.md · "
    "сценарий 02-omni-publish.md."
)

CHANNELS = [
    {
        "slug": "gdepar",
        "project_title": "Empire · Gdepar",
        "checklist_title": "Ритуал · Gdepar (еженедельно)",
        "agent_ref": "empire:channel:gdepar",
        "description": (
            "Канал «Где Пар?» (gdepar.ru): автопосты бань, трафик на карту, ассистент «Пар?». "
            "Монетизация: реклама сайта в TG (docs/channel_monetization.md). "
            "Источник: 07-gdepar.md · финмодель: трафик→Метрика→gdepar. "
            + AUTOPOST_NOTE
        ),
        "tasks": [
            {
                "title": "A1: анти-повторы и клише в постах",
                "status": "todo",
                "note": (
                    "След. шаг: прогнать черновики queue через A1-фильтр.\n"
                    "Проект: Gdepar · контент.\n"
                    "Источник: 07-gdepar.md 🔄 · pipeline контент-завода.\n"
                    "Финмодель: качество постов → удержание → переходы на gdepar.ru.\n"
                    + AUTOPOST_NOTE
                ),
            },
            {
                "title": "Контент gdepar/queue/ + слоты автопоста",
                "status": "todo",
                "note": (
                    "След. шаг: проверить очередь content/gdepar/queue/ и слоты gdepar в auto_publish.json.\n"
                    "Проект: Gdepar · контент-пайплайн.\n"
                    "Автопост уже включён для всех каналов — задача владельца: не допускать пустой queue.\n"
                    "Источник: 07-gdepar.md 🔄 · 02-omni-publish.md.\n"
                    "Финмодель: без очереди слоты автопоста пропускаются → нет трафика."
                ),
            },
            {
                "title": "Почта на сайте gdepar.ru",
                "status": "todo",
                "note": (
                    "След. шаг: настроить почту/форму обратной связи на домене.\n"
                    "Проект: Gdepar · инфраструктура.\n"
                    "Источник: 07-gdepar.md 📝 · Медиаимперия «Почтовый сервер neverretire» (аналог).\n"
                    "Финмодель: доверие и B2B-лиды для рекламодателей карты."
                ),
            },
            {
                "title": "YANDEX_METRIKA_ID + цели на gdepar.ru",
                "status": "todo",
                "note": (
                    "След. шаг: создать счётчик, прописать в .env, цели — docs/metrika_goals_setup.md.\n"
                    "Проект: Gdepar · аналитика (блок «владелец»).\n"
                    "Источник: 07-gdepar.md ⏸ · REMINDERS неделя 1.\n"
                    "Финмодель: без Метрики нет KPI воронки assistant→phone/pick."
                ),
            },
            {
                "title": "Неделя 1: проверка «Пар?» и OpenRouter",
                "status": "todo",
                "note": (
                    "След. шаг: smoke-тест ассистента, ключ OpenRouter, логи.\n"
                    "Проект: Gdepar · продукт.\n"
                    "Источник: 07-gdepar.md ⏸ · gdepar_checkpoints.\n"
                    "Финмодель: ассистент — конверсия в использование карты."
                ),
            },
            {
                "title": "Решение по GDEPAR_ASSISTANT_LLM_PCT (сейчас 25%)",
                "status": "todo",
                "note": (
                    "След. шаг: через 2–4 недели сравнить cost/quality, зафиксировать %.\n"
                    "Проект: Gdepar · экономика LLM.\n"
                    "Источник: 07-gdepar.md ⏸ · REMINDERS 2–4 недели.\n"
                    "Финмодель: доля LLM-ответов влияет на маржу канала."
                ),
            },
            {
                "title": "Техника: Пар?, SSE, health, ≥200 бань, deploy",
                "status": "done",
                "note": (
                    "Выполнено по сценарию 2026-06-11.\n"
                    "Источник: 07-gdepar.md ✅ · Obsidian progress 64%."
                ),
            },
        ],
        "ritual_items": [
            (
                "Проверить /health и SSE ассистента",
                "Источник: 07-gdepar ✅ техника · еженедельный smoke.",
            ),
            (
                "Автопост gdepar: слоты в auto_publish.json + логи публикаций",
                "02-omni-publish · все каналы в едином пайплайне с июня 2026.",
            ),
            (
                "Счётчик постов в gdepar/queue/ (цель >0)",
                "Пайплайн контента · автопост забирает из queue по расписанию.",
            ),
            (
                "Просмотреть UTM и Метрику (если ID есть)",
                "Источник: 13-finance-business · воронка gdepar.",
            ),
            (
                "Проверить GDEPAR_ASSISTANT_LLM_PCT в логах",
                "Источник: 07-gdepar ⏸ · контроль расходов LLM.",
            ),
        ],
    },
    {
        "slug": "pension",
        "project_title": "Empire · Pension",
        "checklist_title": "Ритуал · Pension (еженедельно)",
        "agent_ref": "empire:channel:pension",
        "description": (
            "Канал «На пенсию никогда» (neverretire.ru): книга, YouTube, лонгриды, RAG. "
            "Монетизация: инфопродукт PDF, tripwire (docs/channel_monetization.md). "
            "Источник: 08-pension.md · финмодель: контент→email→продажа книги/курса. "
            + AUTOPOST_NOTE
        ),
        "tasks": [
            {
                "title": "Контент pension/queue/ + слоты автопоста",
                "status": "todo",
                "note": (
                    "След. шаг: дописать посты в content/pension/queue/, проверить слоты pension в auto_publish.json.\n"
                    "Проект: Pension · контент.\n"
                    "Автопост включён — raw_news и curated идут по расписанию.\n"
                    "Источник: 08-pension.md 🔄 · 02-omni-publish.md.\n"
                    "Финмодель: регулярный TG → прогрев к книге/YouTube."
                ),
            },
            {
                "title": "PDF книги + страница /buy",
                "status": "todo",
                "note": (
                    "След. шаг: выложить PDF, кнопка оплаты, YooKassa/лид.\n"
                    "Проект: Pension · монетизация.\n"
                    "Источник: 08-pension.md 🔄 · launch окт 2026.\n"
                    "Финмодель: tripwire → основной доход канала."
                ),
            },
            {
                "title": "Метрика neverretire.ru + цели",
                "status": "todo",
                "note": (
                    "След. шаг: счётчик, цели вебвизора/покупки.\n"
                    "Проект: Pension · аналитика.\n"
                    "Источник: 08-pension.md ⬜ ⏸.\n"
                    "Финмодель: 13-finance-business «Metrika оба сайта»."
                ),
            },
            {
                "title": "YouTube канал + съёмка yt-001",
                "status": "todo",
                "note": (
                    "След. шаг: создать канал, снять первый ролик по готовому сценарию.\n"
                    "Проект: Pension · YouTube.\n"
                    "Источник: 08-pension.md ⬜ · сценарий yt-001 уже ✅.\n"
                    "Финмодель: 12 роликов к launch книги."
                ),
            },
            {
                "title": "12 роликов + launch книги (окт 2026)",
                "status": "todo",
                "note": (
                    "След. шаг: план yt-002…012, даты публикации.\n"
                    "Проект: Pension · веха launch.\n"
                    "Источник: 08-pension.md ⬜ · empire-audit milestones.\n"
                    "Финмодель: Грубая финмодель — доходы от инфопродукта Q4."
                ),
            },
            {
                "title": "Voice RAG (Antonov / Crimson)",
                "status": "todo",
                "note": (
                    "След. шаг: подключить голосовой RAG к базе знаний.\n"
                    "Проект: Pension · продукт.\n"
                    "Источник: 08-pension.md ⬜.\n"
                    "Финмодель: дифференциация контента, удержание."
                ),
            },
            {
                "title": "Сценарии yt-002–012, превью, /buy",
                "status": "todo",
                "note": (
                    "След. шаг: пакетная генерация сценариев и обложек.\n"
                    "Источник: 08-pension.md 📝.\n"
                    "Связь: задачи выше (YouTube + PDF)."
                ),
            },
            {
                "title": "База: книга, Crimson RAG, Мячин, yt-001, 5 лонгридов, raw_news",
                "status": "done",
                "note": "Выполнено · 08-pension.md ✅ · Obsidian progress 43%.",
            },
        ],
        "ritual_items": [
            (
                "Автопост pension: слоты + логи (raw_news / curated)",
                "02-omni-publish · единый пайплайн всех каналов.",
            ),
            ("Проверить pension/queue/ (сколько постов)", "08-pension 🔄 · подпитка автопоста."),
            ("Статус /buy и PDF", "Монетизация · финмодель доход."),
            ("Прогресс YouTube (сколько из 12)", "08-pension ⬜ · веха окт 2026."),
            ("Пенсионные KPI в finance_ledger", "13-finance-business · pension_weekly_metrics."),
        ],
    },
    {
        "slug": "finance",
        "project_title": "Empire · Финансы",
        "checklist_title": "Ритуал · Финансы Empire (воскресенье)",
        "agent_ref": "empire:channel:finance",
        "description": (
            "Общий финконтур двух каналов: ledger, KPI, НПД, Метрика. "
            "Источник: 13-finance-business.md · data/empire_finance_ledger.json · "
            "Грубая финмодель (Медиаимперия). "
            + AUTOPOST_NOTE
        ),
        "tasks": [
            {
                "title": "Заполнить empire_weekly_kpi (сейчас пусто)",
                "status": "todo",
                "note": (
                    "След. шаг: шаблон templates/empire_weekly_kpi_template.csv → data/.\n"
                    "Проект: Финансы · отчётность.\n"
                    "Источник: 13-finance-business.md ⬜.\n"
                    "Финмодель: сводка доходов Pension+Gdepar vs расходы VPS/реклама."
                ),
            },
            {
                "title": "НПД: категория и ИП для верификации",
                "status": "todo",
                "note": (
                    "След. шаг: подать НПД, связать с ЮKassa (супруга/ИП по ТЗ).\n"
                    "Источник: 13-finance-business.md · План Медиаимперия «Юридический блок».\n"
                    "Финмодель: легализация приёма платежей за инфопродукты."
                ),
            },
            {
                "title": "Метрика на обоих сайтах (neverretire + gdepar)",
                "status": "todo",
                "note": (
                    "След. шаг: два счётчика, цели, связка с KPI.\n"
                    "Источник: 13-finance-business.md · задачи каналов ⏸.\n"
                    "Финмодель: единая воронка медиаимперии."
                ),
            },
            {
                "title": "finance_ledger + pension_weekly_metrics",
                "status": "done",
                "note": "Выполнено · 13-finance-business.md ✅ · ledger в data/.",
            },
        ],
        "ritual_items": [
            (
                "Воскресный обзор KPI (доход/расход/воронка)",
                "13-finance-business ⬜ · scripts/empire_finance_simulator.py.",
            ),
            (
                "Обновить empire_finance_ledger.json",
                "Источник: finance_ledger.py · фактические траты VPS и др.",
            ),
            (
                "Сверить Метрику Pension и Gdepar",
                "Связь с проектами каналов · цели конверсии.",
            ),
            (
                "Автопост все каналы: нет ли пропусков слотов за неделю",
                "02-omni-publish · garden/gdepar/stern/lenin/pension в auto_publish.json.",
            ),
            (
                "Проверить вехи empire-audit в календаре",
                "Финмодель: milestones Q3–Q4 2026 launch.",
            ),
        ],
    },
]

OMNI_CHECKLIST = {
    "title": "Ритуал · Автопост все каналы (ежедневно)",
    "agent_ref": "empire:omni-publish",
    "description": (
        "Единый автопостинг всех каналов Empire (июнь 2026). "
        "Источник: 02-omni-publish.md · data/auto_publish.json · "
        "docs/empire_autopost_strategy_2026.md."
    ),
    "tags": ["empire", "autopost", "omni", "ритуал"],
    "items": [
        (
            "Проверить cron/сервис автопоста (логи за 24ч, нет ошибок TG)",
            "02-omni-publish · main.py scheduled publish.",
        ),
        (
            "Все 5 персон включены: garden, gdepar, stern, lenin, pension",
            "data/auto_publish.json · scheduled_only=false для активных слотов.",
        ),
        (
            "Очереди не пустые: gdepar/queue, pension/queue, stern topics",
            "Автопост не генерирует из воздуха — нужен контент в queue/рубриках.",
        ),
        (
            "Curated-рубрики: lenin 12:00, gdepar 12:00, stern 09:00",
            "scripts/activate_curated_rubrics.sh · JSON рубрик.",
        ),
        (
            "При сбое: smoke E2E publish одного слота",
            "docs/empire_autopost_strategy_2026.md § troubleshooting.",
        ),
    ],
}


def _upsert_project(title: str, description: str) -> int:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT id FROM projects WHERE title = ?", (title,)).fetchone()
    if row:
        pid = int(row["id"])
        conn.execute(
            "UPDATE projects SET description = ?, updated_at = datetime('now') WHERE id = ?",
            (description, pid),
        )
    else:
        cur = conn.execute(
            "INSERT INTO projects (title, description, updated_at) VALUES (?, ?, datetime('now'))",
            (title, description),
        )
        pid = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return pid


def _task_by_source(source: str) -> int | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM tasks WHERE obsidian_source = ? LIMIT 1", (source,)
    ).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def _sync_ritual_items(checklist_title: str, items: list[tuple[str, str]]) -> None:
    """Обновить пункты существующего ритуала (пересоздать items)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM checklists WHERE title = ? LIMIT 1", (checklist_title,)
    ).fetchone()
    if not row:
        conn.close()
        return
    cl_id = int(row["id"])
    conn.execute("DELETE FROM checklist_items WHERE checklist_id = ?", (cl_id,))
    for i, (title, comment) in enumerate(items):
        conn.execute(
            """
            INSERT INTO checklist_items (checklist_id, title, sort_order, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (cl_id, f"{title} — {comment}", i),
        )
    conn.execute(
        "UPDATE checklists SET updated_at = datetime('now') WHERE id = ?", (cl_id,)
    )
    conn.commit()
    conn.close()


def _import_channel(ch: dict, *, sync: bool = False) -> dict[str, int]:
    pid = _upsert_project(ch["project_title"], ch["description"])
    tasks_new = tasks_skip = tasks_synced = 0
    for i, t in enumerate(ch["tasks"]):
        source = f"empire:obsidian:{ch['slug']}:{i}"
        existing = _task_by_source(source)
        if existing:
            tasks_skip += 1
            if sync:
                update_task(
                    existing,
                    title=t["title"],
                    note=t.get("note"),
                    project_id=pid,
                )
                if t.get("status") == "done":
                    update_task_status(existing, "done")
                tasks_synced += 1
            continue
        tid = add_task(
            t["title"],
            project_id=pid,
            note=t.get("note"),
            status=t.get("status", "todo"),
            tags=[ch["slug"], "empire"],
            obsidian_source=source,
        )
        if t.get("status") == "done":
            update_task_status(tid, "done")
        tasks_new += 1

    existing_cls = {c["title"].lower(): c["id"] for c in list_checklists(status=None, limit=200)}
    cl_title = ch["checklist_title"]
    if cl_title.lower() not in existing_cls:
        items = [f"{title} — {comment}" for title, comment in ch["ritual_items"]]
        create_checklist(
            cl_title,
            description=(
                f"Повторяемый ритуал канала {ch['slug']}. "
                f"Источник: Empire/_scenarios/checklists/. "
                f"Связанный проект: {ch['project_title']}."
            ),
            source="obsidian",
            agent_ref=ch["agent_ref"],
            tags=["empire", ch["slug"], "ритуал"],
            items=items,
        )
        checklists_new = 1
    else:
        if sync:
            _sync_ritual_items(cl_title, ch["ritual_items"])
        checklists_new = 0

    return {
        "project_id": pid,
        "tasks_new": tasks_new,
        "tasks_skip": tasks_skip,
        "tasks_synced": tasks_synced,
        "checklists_new": checklists_new,
    }


def _import_omni_checklist(*, sync: bool = False) -> int:
    oc = OMNI_CHECKLIST
    existing_cls = {c["title"].lower(): c["id"] for c in list_checklists(status=None, limit=200)}
    if oc["title"].lower() not in existing_cls:
        items = [f"{t} — {c}" for t, c in oc["items"]]
        create_checklist(
            oc["title"],
            description=oc["description"],
            source="obsidian",
            agent_ref=oc["agent_ref"],
            tags=oc["tags"],
            items=items,
        )
        return 1
    if sync:
        _sync_ritual_items(oc["title"], oc["items"])
    return 0


def unmerge_ticktick_from_empire() -> int:
    """Вернуть в Inbox все TickTick-задачи, ошибочно попавшие в проекты Empire."""
    init_db()
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT t.id FROM tasks t
        JOIN projects p ON p.id = t.project_id
        WHERE p.title LIKE 'Empire ·%'
          AND (t.obsidian_source LIKE 'ticktick:%'
               OR t.tags LIKE '%merged-from-inbox%')
        """
    ).fetchall()
    for row in rows:
        conn.execute(
            "UPDATE tasks SET project_id = NULL, updated_at = datetime('now') WHERE id = ?",
            (int(row["id"]),),
        )
    conn.commit()
    conn.close()
    return len(rows)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Обновить описания проектов, заметки задач и пункты ритуалов",
    )
    parser.add_argument(
        "--unmerge-ticktick",
        action="store_true",
        help="Отвязать ticktick:* задачи от проектов Empire ·",
    )
    args = parser.parse_args()

    init_db()
    if args.unmerge_ticktick:
        n = unmerge_ticktick_from_empire()
        print(f"unmerged {n} ticktick tasks from Empire projects")

    totals = {"tasks_new": 0, "tasks_synced": 0, "checklists_new": 0}
    for ch in CHANNELS:
        r = _import_channel(ch, sync=args.sync)
        print(ch["project_title"], r)
        totals["tasks_new"] += r["tasks_new"]
        totals["tasks_synced"] += r["tasks_synced"]
        totals["checklists_new"] += r["checklists_new"]
    omni = _import_omni_checklist(sync=args.sync)
    totals["checklists_new"] += omni
    if omni:
        print(OMNI_CHECKLIST["title"], "created")
    print("TOTAL", totals)


if __name__ == "__main__":
    main()
