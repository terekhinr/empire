#!/usr/bin/env python3
"""
Seed planning PWA из пакета аудита docs/audit/:

  — цель Empire 2026–27
  — проект «Empire · Финансовая модель» с пояснениями
  — чеклисты: итоговый %, по фазам, cashflow, допущения, метрики
  — вехи с датами → календарь

  ./venv/bin/python scripts/seed_empire_pipeline_2026.py
  ./venv/bin/python scripts/seed_empire_pipeline_2026.py --force
  ./venv/bin/python scripts/seed_empire_pipeline_2026.py --sync
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_DATA_PATH = Path(__file__).resolve().parent / "empire_finance_model_seed_data.py"
_spec = importlib.util.spec_from_file_location("empire_finance_model_seed_data", _DATA_PATH)
assert _spec and _spec.loader
_fm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fm)

BLOCK_REF_MAP_EXTRA = _fm.BLOCK_REF_MAP_EXTRA
EXTRA_CHECKLISTS = _fm.EXTRA_CHECKLISTS
FINANCE_MODEL_PROJECT_DESC = _fm.FINANCE_MODEL_PROJECT_DESC
FINANCE_MODEL_PROJECT_TITLE = _fm.FINANCE_MODEL_PROJECT_TITLE
FINANCE_MODEL_TASKS = _fm.FINANCE_MODEL_TASKS

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

GOAL_TITLE = "Empire · 100k ₽/мес к ноябрю 27"
TRACKER = ROOT / "docs" / "audit" / "09_PROGRESS_TRACKER.md"

ITEM_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*\[\s*[xX ]?\s*\]\s*\|\s*(.+?)\s*\|\s*$"
)
BLOCK_RE = re.compile(r"^## (Блок .+?) ·")

MANAGED_REFS = (
    "empire-pipeline-2026",
    "empire-pipeline-phase-0",
    "empire-pipeline-phase-1",
    "empire-pipeline-phase-2",
    "empire-pipeline-phase-3",
    "empire-audit-tech-p0",
    "empire-audit-media-roi",
    "empire-finance-assumptions",
    "empire-finance-cashflow",
    "empire-finance-metrics",
    "empire-block-0",
    "empire-block-a",
    "empire-block-b",
    "empire-block-c",
    "empire-block-d",
    "empire-block-e",
    "empire-block-f",
    "empire-block-g",
)

PROJECTS: list[tuple[str, str, str]] = [
    ("Bridge · 35k Q4", "Блок 0", "Резерв 35 000 ₽ на Директ · см. раздел Финмодель"),
    ("Пенсия · Книга", "Блок B", "Черновик → launch 299₽ 15 сен · 25% трекера"),
    ("Пенсия · Медиа YT", "Блок C", "YT с 1 сен · нативка 8k апр 27 · 20% трекера"),
    ("Где Пар · Данные", "Блок D", "500 published · SEO · enrich · 10% трекера"),
    ("Где Пар · Монетизация", "Блок E", "НПД · триал · Premium · 25% трекера"),
    ("Инфра · Метрика", "Блок A", "Metrika pension/gdepar · 50+ лидов · 5%"),
    ("Спутники TG", "Блок F", "Автопост 5 TG ✅ · queue · KPI · CTA · 10% трекера"),
    ("Метрики · KPI", "Блок G", "weekly_kpi · Метрика · gift_emails · 10% трекера"),
    ("Тех · Автопост RAG", "Аудит 01", "Срез слотов · evaluate_rag · метрики денег"),
]

PHASE_CHECKLISTS: list[tuple[str, str, str, list[str]]] = [
    (
        "empire-pipeline-phase-0",
        "Фаза 0 · Июн–Сен 2026",
        "08_PIPELINE_YEAR · Книга + TG, Где Пар парсинг, 0 продаж",
        [
            "[Июн] Книга: +2 главы → 100% черновика",
            "[Июн] ✅ Автопост 5 TG (auto_publish.json)",
            "[Июн] YANDEX_METRIKA_ID на neverretire.ru",
            "[Июн] Не делать: массовый YT, outreach баням",
            "[Июн] Gdepar: cron парсера / published OK",
            "[Июн] KPI: 386→500 published (фон)",
            "[Июн] Ритуал: tg_posts_published в KPI недели",
            "[Июл] Beta: 5 читателей, 3 отзыва",
            "[Июл] Финал редактуры книги 100%",
            "[Июл] Email-база: 50 адресов",
            "[Июл] Gdepar: Yandex enrich топ-регионов",
            "[Июл] Gdepar: 0 звонков, 0 Premium",
            "[Авг] Pre-sale /buy 149₽ — 15–25 продаж",
            "[Авг] Посевы TG 5–7k → /gift → 50–80 email",
            "[Авг] Снять + смонтировать 2 YT (публикация в сен)",
            "[Авг] PDF «5 принципов» + лендинг (pension_august_funnel)",
            "[Авг] Gdepar: 5–10 SEO-статей закладка",
            "[Авг] Gdepar: CPA-оферта (триал топ-бани)",
            "[Сен] 01.09: публикация YT №1",
            "[Сен] 08.09: YT №2 + email-прогрев",
            "[Сен] 15.09: Launch PDF 299₽ — 30–40 продаж",
            "[Сен] Bridge 35 000 ₽ на счёте",
            "[Сен] До 01.10: НПД супруги + ЮKassa gdepar",
        ],
    ),
    (
        "empire-pipeline-phase-1",
        "Фаза 1 · Окт–Дек 2026",
        "08_PIPELINE_YEAR · YT + CPA · Директ · триал 3 звонка",
        [
            "[Окт] YT: 4 выпуска — CTA только книга 399₽",
            "[Окт] EPUB Литрес (неэксклюзив)",
            "[Окт] Медиакит v1 (для апр 27, не декабря)",
            "[Окт] Директ 12k (bridge + книга)",
            "[Окт] Триал 3 звонка → блок (gdepar_cpa_deposit.md)",
            "[Окт] Коллтрекинг на НПД супруги",
            "[Ноя] YT 1/нед; outreach брокерам",
            "[Ноя] 15.11: стоп-лосс CPL >450₽/7д → стоп или ≤6k",
            "[Ноя] 20 бесплатных Premium — топ-бани",
            "[Ноя] Депозиты CPA: ещё 1–2 пакета",
            "[Ноя] KPI: кейс «N звонков >45 сек»",
            "[Дек] YT → книга; без внешней нативки",
            "[Дек] Gdepar: депозиты после триала",
            "[Дек] Подготовка Premium (продажи с февраля)",
        ],
    ),
    (
        "empire-pipeline-phase-2",
        "Фаза 2 · Янв–Май 2027",
        "08_PIPELINE_YEAR · Premium · первая нативка · 50–70k/мес",
        [
            "[Янв] YT + доработка книги 399₽",
            "[Янв] 1–15 янв: 0 активных B2B-продаж",
            "[Янв] Автоматизация отчётов, бэкап, коллтрек",
            "[Фев] 10–28: первые Premium + депозиты (НПД)",
            "[Мар] 3–4 Premium/мес старт (churn 12%)",
            "[Апр] Первая внешняя нативка YT 8k",
            "[Май] Промежуточная цель: 50–70k ₽/мес суммарно",
            "[Май] 6–8 active Premium Gdepar",
            "[Q1-Q2] Книга 399₽ стабильные продажи",
            "[Q1-Q2] Холодный outreach: конверсия 1–2%, не 5%",
        ],
    ),
    (
        "empire-pipeline-phase-3",
        "Фаза 3 · Июн–Ноя 2027",
        "08_PIPELINE_YEAR · Масштаб · 100k ₽/мес",
        [
            "[Июн–Окт] Нативки 20–25k/мес",
            "[Июн–Окт] 12→15 active Premium",
            "[Июн–Окт] Доход Σ 90–100k/мес к осени",
            "[Ноя] 15 Premium + CPA стабильно",
            "[Ноя] Цель: ~105k ₽/мес net (стретч 100k)",
            "[Ноя] YT стабильный · книга как trust asset",
        ],
    ),
]

TECH_AUDIT_ITEMS = [
    "[P0] content_config: Stern/Garden → 7–10 пост/нед + CTA флагманы",
    "[P0] evaluate_rag.py в CI раз в неделю (faithfulness <3 → стоп LLM)",
    "[P0] Метрики: gdepar лиды + продажи книги + нативки (не «посты вышли»)",
    "[P1] Выключить spy/нейро на Сад/Ленин",
    "[P1] Рефактор main.py: промпты без god-file регрессий",
    "[Keep] gdepar_app, парсеры OSM/Yandex — доить",
    "[Keep] curated: classic_banya, lenin PSS, raw_news Pension",
    "[Cut] LLM Garden/Stern с 48 до 7–10 слотов/нед",
]

MEDIA_ROI_ITEMS = [
    "[Неделя] Gdepar: outreach 20 владельцев → 1 Premium 2990₽",
    "[Неделя] Pension: pre-sale 149₽ → 10 копий",
    "[Не делать] Покупка подписчиков до PMF",
    "[Не делать] Масштаб рекламы до product-market fit",
    "Gdepar TG: 10–14/нед, UTM на gdepar.ru",
    "Pension TG: raw_news + редкий ANALYSIS (не объём)",
    "Garden/Stern: спутники → neverretire.ru",
    "Lenin: минимум API, хобби/донаты",
    "Пивот: 2 флагмана (Gdepar B2B + Pension книга); TG = lead-magnets",
]

BLOCK_REF_MAP = {
    "Блок 0": "empire-block-0",
    "Блок A": "empire-block-a",
    "Блок B": "empire-block-b",
    "Блок C": "empire-block-c",
    "Блок D": "empire-block-d",
    "Блок E": "empire-block-e",
    "Блок F": "empire-block-f",
    **BLOCK_REF_MAP_EXTRA,
}

MILESTONES: list[tuple[str, str, str, str, int]] = [
    # title, due_date, project_title, note, priority
    (
        "Веха: gift_emails ≥50 (/gift)",
        "2026-08-31",
        "Пенсия · Книга",
        "14_PIPELINE_R5_AUTOPOST · воронка launch",
        2,
    ),
    (
        "Веха: /buy pre-sale 149₽ открыт",
        "2026-08-01",
        "Пенсия · Книга",
        "Tripwire перед launch",
        2,
    ),
    (
        "Веха: Метрика pension + gdepar",
        "2026-07-15",
        "Метрики · KPI",
        "09_PROGRESS_TRACKER Блок A+G",
        3,
    ),
    (
        "Веха: 500 published MO/MSK/SPB",
        "2026-09-30",
        "Где Пар · Данные",
        "Блок D · база для SEO/карты",
        2,
    ),
    (
        "Веха: EPUB Литрес",
        "2026-10-15",
        "Пенсия · Книга",
        "249₽ неэксклюзив · роялти 25–30%",
        1,
    ),
    (
        "Веха: черновик книги 100%",
        "2026-06-30",
        "Пенсия · Книга",
        "09_PROGRESS_TRACKER · Блок B",
        2,
    ),
    (
        "Веха: 5 beta + 3 отзыва",
        "2026-07-31",
        "Пенсия · Книга",
        "04_STRATEGY · конец июля",
        2,
    ),
    (
        "Веха: pre-sale 149₽ (15–25 продаж)",
        "2026-08-31",
        "Пенсия · Книга",
        "08_PIPELINE_YEAR · август",
        3,
    ),
    (
        "Веха: YT №1 публикация",
        "2026-09-01",
        "Пенсия · Медиа YT",
        "Смонтирован в августе",
        2,
    ),
    (
        "Веха: YT №2 + email-прогрев",
        "2026-09-08",
        "Пенсия · Медиа YT",
        "",
        2,
    ),
    (
        "Веха: Launch книга 299₽ (30+ продаж)",
        "2026-09-15",
        "Пенсия · Книга",
        "15 сен · bridge 35k параллельно",
        3,
    ),
    (
        "Веха: Bridge 35 000 ₽ на счёте",
        "2026-09-30",
        "Bridge · 35k Q4",
        "07_PIPELINE_BLOCKS · Блок 0",
        3,
    ),
    (
        "Веха: НПД супруги + ЮKassa gdepar",
        "2026-10-01",
        "Где Пар · Монетизация",
        "13_GEMINI_R4 · не ИП",
        3,
    ),
    (
        "Веха: стоп-лосс CPL Директ",
        "2026-11-15",
        "Где Пар · Монетизация",
        "CPL >450₽/7д → стоп или бюджет ≤6k",
        3,
    ),
    (
        "Веха: 20 free Premium выдано",
        "2026-11-30",
        "Где Пар · Монетизация",
        "Топ-бани · бэклинки",
        2,
    ),
    (
        "Веха: первые Premium (10–28 фев)",
        "2027-02-28",
        "Где Пар · Монетизация",
        "Не продавать в январе 1–15",
        3,
    ),
    (
        "Веха: 1-я нативка YT 8k",
        "2027-04-30",
        "Пенсия · Медиа YT",
        "5k+ subs prerequisite",
        2,
    ),
    (
        "Промежуток: 50–70k ₽/мес",
        "2027-05-31",
        "Пенсия · Книга",
        "05_FINANCIAL_MODEL · май 27",
        2,
    ),
    (
        "Цель: 100k ₽/мес net",
        "2027-11-30",
        "Пенсия · Книга",
        "Стретч · 15 Premium Gdepar + книга + нативки",
        3,
    ),
]


def _find_goal_id(title: str) -> int | None:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT id FROM goals WHERE title = ?", (title,)).fetchone()
    if not row:
        row = conn.execute(
            "SELECT id FROM goals WHERE title LIKE 'Empire%' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def _update_goal(goal_id: int, title: str, description: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE goals SET title=?, description=?, updated_at=datetime('now') WHERE id=?",
        (title, description, goal_id),
    )
    conn.commit()
    conn.close()


def _find_project_id(title: str) -> int | None:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT id FROM projects WHERE title = ?", (title,)).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def _archive_checklist(cid: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE checklists SET status='archived', updated_at=datetime('now') WHERE id=?",
        (cid,),
    )
    conn.commit()
    conn.close()


def _parse_tracker_items() -> list[str]:
    if not TRACKER.is_file():
        raise FileNotFoundError(TRACKER)
    items: list[str] = []
    for line in TRACKER.read_text(encoding="utf-8").splitlines():
        m = ITEM_RE.match(line.strip())
        if m:
            weight, title = m.group(1), m.group(2).strip()
            items.append(f"[{weight}%] {title}")
    if not items:
        raise ValueError(f"No checklist items parsed from {TRACKER}")
    return items


def _parse_tracker_by_block() -> dict[str, list[str]]:
    if not TRACKER.is_file():
        raise FileNotFoundError(TRACKER)
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in TRACKER.read_text(encoding="utf-8").splitlines():
        bm = BLOCK_RE.match(line.strip())
        if bm:
            header = bm.group(1)
            key = header.split("·", 1)[0].strip()
            current = key
            blocks.setdefault(current, [])
            continue
        m = ITEM_RE.match(line.strip())
        if m and current:
            weight, title = m.group(1), m.group(2).strip()
            blocks[current].append(f"[{weight}%] {title}")
    return blocks


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
        tags=tags or ["empire", "audit", "2026"],
        items=items,
    )
    print(f"  created checklist: {agent_ref} id={cid} ({len(items)} items)")
    return cid


def _upsert_finance_project(goal_id: int | None, description: str) -> int:
    """Один проект финмодели; переименование со старого заголовка."""
    new_title = FINANCE_MODEL_PROJECT_TITLE
    old_title = "Empire · Финансовая модель"
    pid = _find_project_id(new_title) or _find_project_id(old_title)
    if pid is None:
        pid = add_project(new_title, goal_id=goal_id, description=description)
        print(f"  created: {new_title} id={pid}")
        return pid
    conn = get_connection()
    conn.execute(
        "UPDATE projects SET title=?, description=?, goal_id=?, updated_at=datetime('now') WHERE id=?",
        (new_title, description, goal_id, pid),
    )
    conn.commit()
    conn.close()
    print(f"  updated: {new_title} id={pid}")
    return pid


def _upsert_project(title: str, goal_id: int | None, description: str) -> int:
    pid = _find_project_id(title)
    if pid is None:
        pid = add_project(title, goal_id=goal_id, description=description)
        print(f"  created: {title} id={pid}")
        return pid
    conn = get_connection()
    conn.execute(
        "UPDATE projects SET description=?, goal_id=?, updated_at=datetime('now') WHERE id=?",
        (description, goal_id, pid),
    )
    conn.commit()
    conn.close()
    print(f"  updated: {title} id={pid}")
    return pid


def _task_by_source(source: str) -> int | None:
    init_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM tasks WHERE obsidian_source = ? LIMIT 1", (source,)
    ).fetchone()
    conn.close()
    return int(row["id"]) if row else None


def _ensure_finance_task(
    title: str,
    due_date: str,
    project_id: int | None,
    goal_id: int | None,
    note: str,
    priority: int,
    tags: list[str],
    source_key: str,
    *,
    sync: bool = False,
) -> None:
    existing_id = _task_by_source(source_key)
    if existing_id:
        if sync:
            update_task(
                existing_id,
                title=title,
                note=note,
                due_date=due_date,
                project_id=project_id,
                goal_id=goal_id,
                priority=priority,
                tags=tags,
            )
            print(f"  finance task synced: {due_date} {title[:45]}")
        else:
            print(f"  finance task exists: {title[:45]}")
        return
    tid = add_task(
        title,
        project_id=project_id,
        goal_id=goal_id,
        due_date=due_date,
        priority=priority,
        note=note or None,
        tags=tags,
        obsidian_source=source_key,
    )
    print(f"  finance task id={tid}: {due_date} {title[:50]}")


def _milestone_source(due_date: str, title: str) -> str:
    slug = re.sub(r"[^\w]+", "-", title.lower())[:40].strip("-")
    return f"empire-audit:milestone:{due_date}:{slug}"


def _ensure_milestone(
    title: str,
    due_date: str,
    project_id: int | None,
    goal_id: int | None,
    note: str,
    priority: int,
    *,
    sync: bool = False,
) -> None:
    source = _milestone_source(due_date, title)
    existing_id = _task_by_source(source)
    if existing_id:
        if sync:
            update_task(
                existing_id,
                title=title,
                note=note or None,
                due_date=due_date,
                project_id=project_id,
                goal_id=goal_id,
                priority=priority,
            )
            print(f"  milestone synced: {due_date} {title[:40]}")
        else:
            print(f"  milestone exists: {due_date} {title[:40]}")
        return
    tid = add_task(
        title,
        project_id=project_id,
        goal_id=goal_id,
        due_date=due_date,
        priority=priority,
        note=note or None,
        tags=["empire", "веха", "audit"],
        obsidian_source=source,
    )
    print(f"  milestone id={tid}: {due_date} {title[:50]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Empire audit → planning PWA")
    parser.add_argument(
        "--force",
        action="store_true",
        help="пересоздать все чеклисты пакета (старые → archived)",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="обновить описания проектов и заметки задач (без пересоздания чеклистов)",
    )
    args = parser.parse_args()

    if not args.force and find_checklist_by_ref("empire-pipeline-2026"):
        print("Чеклисты уже есть — пропуск (добавь --force для пересоздания).")
        print("Проекты и вехи обновляются идемпотентно.\n")
        skip_checklists = True
    else:
        skip_checklists = False

    goal_desc = (
        "Май 27: 50–70k/мес. Стретч 100k: ноябрь 2027. "
        "Финмодель: docs/audit/05_FINANCIAL_MODEL.md · R5: 14_PIPELINE_R5_AUTOPOST.md"
    )
    goal_id = _find_goal_id(GOAL_TITLE)
    if goal_id is None:
        goal_id = add_goal(GOAL_TITLE, description=goal_desc, target_date="2027-11-30")
        print(f"created goal id={goal_id}")
    else:
        _update_goal(goal_id, GOAL_TITLE, goal_desc)
        print(f"updated goal id={goal_id}")

    print("\n=== Проекты (блоки) ===")
    project_ids: dict[str, int] = {}
    for proj_title, block, desc in PROJECTS:
        project_ids[proj_title] = _upsert_project(proj_title, goal_id, f"{block} · {desc}")

    print("\n=== Проект · Финмодель ===")
    fm_pid = _upsert_finance_project(goal_id, FINANCE_MODEL_PROJECT_DESC)
    project_ids[FINANCE_MODEL_PROJECT_TITLE] = fm_pid

    if not skip_checklists:
        print("\n=== Чеклисты ===")
        _ensure_checklist(
            "empire-pipeline-2026",
            "Empire Pipeline 2026 · Итоговый %",
            "Веса в пунктах. Прогресс = Σ(вес выполненных). docs/audit/09_PROGRESS_TRACKER.md",
            _parse_tracker_items(),
            tags=["empire", "pipeline", "2026", "weighted"],
            force=args.force,
        )

        for ref, title, desc, items in PHASE_CHECKLISTS:
            _ensure_checklist(
                ref, title, desc, items, tags=["empire", "phase", "2026"], force=args.force
            )

        for ref, title, desc, items in EXTRA_CHECKLISTS:
            _ensure_checklist(
                ref,
                title,
                desc,
                items,
                tags=["empire", "финмодель", "2026"],
                force=args.force,
            )

        _ensure_checklist(
            "empire-audit-tech-p0",
            "Тех-аудит · Автопост RAG P0",
            "docs/audit/01_TECH_RAG_AUDIT.md",
            TECH_AUDIT_ITEMS,
            tags=["empire", "tech", "audit"],
            force=args.force,
        )
        _ensure_checklist(
            "empire-audit-media-roi",
            "Media ROI · Доить / резать",
            "docs/audit/02_ROI_MEDIA_AUDIT.md",
            MEDIA_ROI_ITEMS,
            tags=["empire", "media", "audit"],
            force=args.force,
        )

        blocks = _parse_tracker_by_block()
        for block_key, items in blocks.items():
            ref = BLOCK_REF_MAP.get(block_key)
            if not ref or not items:
                continue
            _ensure_checklist(
                ref,
                f"{block_key} · чеклист",
                "Блок из 09_PROGRESS_TRACKER.md",
                items,
                tags=["empire", "block", block_key[-1].lower()],
                force=args.force,
            )

    print("\n=== Вехи (календарь) ===")
    for title, due, proj_title, note, prio in MILESTONES:
        _ensure_milestone(
            title,
            due,
            project_ids.get(proj_title),
            goal_id,
            note,
            prio,
            sync=args.sync,
        )

    print("\n=== Задачи финмодели (пояснения) ===")
    for t_title, due, prio, tags, source_key, note in FINANCE_MODEL_TASKS:
        _ensure_finance_task(
            t_title,
            due,
            fm_pid,
            goal_id,
            note,
            prio,
            tags,
            source_key,
            sync=args.sync,
        )

    print(
        "\nГотово. PWA: /tasks/ → **Финмодель** (меню) · Проект Empire · Финмодель · Календарь."
    )
    print("Документация: docs/audit/14_PIPELINE_R5_AUTOPOST.md · 05_FINANCIAL_MODEL.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
