#!/usr/bin/env python3
"""
Синхронизация git docs/ и data/*.json → Obsidian vault (Empire/_canon, Empire/_finance).

Не трогает persona/*/queue/ — постинг без изменений.

  ./venv/bin/python scripts/sync_empire_obsidian.py --all
  ./venv/bin/python scripts/sync_empire_obsidian.py --docs
  ./venv/bin/python scripts/sync_empire_obsidian.py --finance
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
VAULT_EMPIRE = ROOT / "data" / "obsidian_vault" / "Empire"
CANON_DIR = VAULT_EMPIRE / "_canon"
FINANCE_DIR = VAULT_EMPIRE / "_finance"

# git docs → имя файла в _canon/
CANON_DOCS: list[tuple[str, str]] = [
    ("PROJECT_OS.md", "00-project-os.md"),
    ("empire_master_plan_rf_2026.md", "master-plan-rf-2026.md"),
    ("empire_master_backlog.md", "master-backlog.md"),
    ("empire_business_plan_2026.md", "business-plan-2026.md"),
    ("empire_content_quality_backlog.md", "content-quality-backlog.md"),
    ("empire_master_checkpoints.md", "master-checkpoints.md"),
    ("empire_decisions_2026-05.md", "decisions-2026-05.md"),
    ("growth_rf_no_max_2026.md", "growth-rf-no-max-2026.md"),
    ("channel_monetization.md", "channel-monetization.md"),
    ("obsidian_practical_guide_ru.md", "obsidian-practical-guide.md"),
    ("empire_obsidian_integration.md", "obsidian-integration.md"),
    ("garden_posting_matrix_2026.md", "garden-posting-matrix-2026.md"),
    ("gdepar_posting_matrix_2026.md", "gdepar-posting-matrix-2026.md"),
    ("garden_growth_rf_no_vpn.md", "garden-growth-rf-no-vpn.md"),
    ("gdepar_checkpoints.md", "gdepar-checkpoints.md"),
    ("REMINDERS_gdepar.md", "reminders-gdepar.md"),
    ("metrika_goals_setup.md", "metrika-goals-setup.md"),
    ("garden_infoproduct_tz.md", "garden-infoproduct-tz.md"),
    ("gdepar_ai_assistant_tz.md", "gdepar-ai-assistant-tz.md"),
    ("pension_book_publish_tz.md", "pension-book-publish-tz.md"),
    ("pension_analytics_accounts_guide.md", "pension-analytics-guide.md"),
    ("pension_youtube_roadmap_12m_2026.md", "pension-youtube-roadmap-12m.md"),
    ("infoproduct_launch_checklist.md", "infoproduct-launch-checklist.md"),
    ("empire_partisan_architecture.md", "partisan-architecture.md"),
    ("empire_kpi_sheets_template.md", "kpi-sheets-template.md"),
    ("posting_matrices_all_channels.md", "posting-matrices-all.md"),
    ("lenin_channel_editorial.md", "lenin-channel-editorial.md"),
    ("TZ_OMNI_MEDIA_EMPIRE_FINAL.md", "TZ-OMNI-MEDIA-EMPIRE-FINAL.md"),
    ("audit/00_INDEX.md", "audit-00-index.md"),
    ("audit/01_TECH_RAG_AUDIT.md", "audit-01-tech-rag.md"),
    ("audit/02_ROI_MEDIA_AUDIT.md", "audit-02-roi-media.md"),
    ("audit/03_DIAGNOSTIC.md", "audit-03-diagnostic.md"),
    ("audit/04_STRATEGY.md", "audit-04-strategy.md"),
    ("audit/05_FINANCIAL_MODEL.md", "audit-05-financial-model.md"),
    ("audit/06_GDEPAR_MARKET.md", "audit-06-gdepar-market.md"),
    ("audit/07_PIPELINE_BLOCKS.md", "audit-07-pipeline-blocks.md"),
    ("audit/08_PIPELINE_YEAR.md", "audit-08-pipeline-year.md"),
    ("audit/09_PROGRESS_TRACKER.md", "audit-09-progress-tracker.md"),
    ("audit/10_REVISION_GEMINI.md", "audit-10-revision-gemini.md"),
    ("audit/11_GEMINI_R2.md", "audit-11-gemini-r2.md"),
    ("audit/12_GEMINI_R3.md", "audit-12-gemini-r3.md"),
    ("audit/13_GEMINI_R4.md", "audit-13-gemini-r4.md"),
    ("audit/14_GEMINI_R5.md", "audit-14-gemini-r5.md"),
    ("pension_august_funnel_2026.md", "pension-august-funnel-2026.md"),
    ("EMPIRE_PIPELINE_PLAYBOOK_RU.md", "empire-pipeline-playbook-ru.md"),
    ("empire_legal_structure.md", "empire-legal-structure.md"),
    ("gdepar_cpa_deposit.md", "gdepar-cpa-deposit.md"),
    ("EMPIRE_STRATEGY_2026.md", "empire-strategy-2026.md"),
    ("EMPIRE_EARNINGS_PLAN_2026.md", "empire-earnings-plan-2026.md"),
    ("gdepar_market_analysis_2026.md", "gdepar-market-analysis-2026.md"),
]

CHECKBOX_RE = re.compile(r"^(\s*)- \[([ xX])\] (.*)$")


def _preserve_checkboxes(old: str, new: str) -> str:
    """Сохранить [x] в Obsidian при обновлении из git (по тексту пункта)."""
    checked: dict[str, bool] = {}
    for line in old.splitlines():
        m = CHECKBOX_RE.match(line)
        if m:
            checked[m.group(3).strip()] = m.group(2).lower() == "x"
    out: list[str] = []
    for line in new.splitlines():
        m = CHECKBOX_RE.match(line)
        if m:
            text = m.group(3).strip()
            if text in checked:
                mark = "x" if checked[text] else " "
                line = f"{m.group(1)}- [{mark}] {m.group(3)}"
        out.append(line)
    return "\n".join(out)


def _canon_header(rel_source: str, dest_name: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""---
tags:
  - empire/canon
  - empire/docs
canon_sync: true
do_not_import: true
source: docs/{rel_source}
obsidian_dest: Empire/_canon/{dest_name}
synced_at: {ts}
---

> **Зеркало git** `docs/{rel_source}` · галочки можно ставить здесь — при следующем `--docs` сохранятся.  
> Правки текста лучше в git `docs/`, затем снова sync.  
> **Постинг:** этот файл **не** импортируется в бот.

---

"""


def sync_docs() -> int:
    CANON_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for src_name, dest_name in CANON_DOCS:
        src = DOCS / src_name
        if not src.is_file():
            print(f"skip missing: {src}", file=sys.stderr)
            continue
        dest = CANON_DIR / dest_name
        body = src.read_text(encoding="utf-8")
        if dest.is_file():
            old = dest.read_text(encoding="utf-8")
            # strip old frontmatter + banner for merge
            if old.startswith("---"):
                parts = old.split("---", 2)
                if len(parts) >= 3:
                    old_body = parts[2].lstrip("\n")
                    if old_body.startswith(">"):
                        idx = old_body.find("\n\n---\n\n")
                        if idx != -1:
                            old_body = old_body[idx + 7 :]
                    body_merged = _preserve_checkboxes(old_body, body)
                    body = body_merged
        content = _canon_header(src_name, dest_name) + body
        if not content.endswith("\n"):
            content += "\n"
        dest.write_text(content, encoding="utf-8")
        n += 1
    _write_canon_index(n)
    print(f"canon: {n} docs → {CANON_DIR}")
    return n


def _write_canon_index(count: int) -> None:
    lines = [
        "---",
        "tags:",
        "  - empire/canon",
        "  - empire/moc",
        "do_not_import: true",
        "---",
        "",
        "# Канон Empire (зеркало git)",
        "",
        f"> Авто-sync: `scripts/sync_empire_obsidian.py --docs` · файлов: **{count}**",
        "",
        "## Ежедневно",
        "",
        "| Документ |",
        "|----------|",
        "| [[00-СЕГОДНЯ]] |",
        "| [[00-ПАЙПЛАЙН]] |",
        "| [[../00-ДОКУМЕНТАЦИЯ]] |",
        "",
        "## Планы и чеклисты",
        "",
    ]
    groups = [
        ("Операции", ["00-project-os.md", "master-plan-rf-2026.md", "master-backlog.md", "master-checkpoints.md"]),
        ("Финансы", ["business-plan-2026.md", "channel-monetization.md", "kpi-sheets-template.md"]),
        ("Контент", ["garden-posting-matrix-2026.md", "gdepar-posting-matrix-2026.md", "content-quality-backlog.md"]),
        ("Pension", ["pension-book-publish-tz.md", "pension-analytics-guide.md", "pension-youtube-roadmap-12m.md"]),
        ("ТЗ", ["TZ-OMNI-MEDIA-EMPIRE-FINAL.md"]),
        ("Obsidian", ["obsidian-practical-guide.md", "obsidian-integration.md"]),
    ]
    for title, files in groups:
        lines.append(f"### {title}")
        lines.append("")
        for f in files:
            stem = Path(f).stem
            lines.append(f"- [[{stem}|{f}]]")
        lines.append("")
    (CANON_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_finance() -> None:
    sys.path.insert(0, str(ROOT))
    from finance_ledger import (  # noqa: WPS433
        EXPENSE_CATEGORY_LABELS,
        build_pl_monthly,
        load_ledger,
        load_weekly_kpi,
        ytd_totals,
    )

    FINANCE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ledger = load_ledger()
    kpi_rows = load_weekly_kpi()
    pl = build_pl_monthly()
    ytd = ytd_totals()

    # Pension metrics optional
    pen_path = ROOT / "data" / "pension_weekly_metrics.json"
    pen_rows: list = []
    if pen_path.is_file():
        try:
            pen_rows = json.loads(pen_path.read_text(encoding="utf-8"))
            if not isinstance(pen_rows, list):
                pen_rows = []
        except json.JSONDecodeError:
            pen_rows = []

    lines: list[str] = [
        "---",
        "tags:",
        "  - empire/finance",
        "do_not_import: true",
        f"synced_at: {ts}",
        "---",
        "",
        "# Финансы и метрики Empire",
        "",
        "> **Обновление:** `scripts/sync_empire_obsidian.py --finance` · источник: `data/empire_finance_ledger.json`, "
        "`empire_weekly_kpi.json`, `sales.db` · дашборд: **Око Саурона → P&L · Финансы**",
        "",
        "См. также: [[чеклист-бизнес-плана]] · канон [[../_canon/business-plan-2026|business-plan-2026]]",
        "",
        "---",
        "",
        "## YTD " + str(ytd.get("year", "")),
        "",
        "| Показатель | ₽ |",
        "|------------|---|",
        f"| Расходы | **{ytd.get('expense_ytd_rub', 0):,.0f}** |",
        f"| Доход (ledger) | {ytd.get('income_ledger_ytd_rub', 0):,.0f} |",
        f"| Доход (sales.db) | {ytd.get('income_sales_ytd_rub', 0):,.0f} |",
        f"| **Доход всего** | **{ytd.get('income_total_ytd_rub', 0):,.0f}** |",
        f"| **Маржа YTD** | **{ytd.get('margin_ytd_rub', 0):,.0f}** |",
        f"| Cursor YTD | {ytd.get('expense_cursor_ytd_rub', 0):,.0f} |",
        f"| OpenRouter YTD | {ytd.get('expense_openrouter_ytd_rub', 0):,.0f} |",
        f"| fal.ai YTD | {ytd.get('expense_fal_ytd_rub', 0):,.0f} |",
        f"| **ИИ-инструменты** | **{ytd.get('expense_ai_tools_ytd_rub', 0):,.0f}** |",
        "",
    ]

    by_cat = ytd.get("expense_by_category") or {}
    if by_cat:
        lines.append("### Расходы по категориям (YTD)")
        lines.append("")
        lines.append("```mermaid")
        lines.append("pie showData")
        lines.append('    title Расходы YTD (₽)')
        for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
            if amt <= 0:
                continue
            label = EXPENSE_CATEGORY_LABELS.get(cat, cat)
            lines.append(f'    "{label}" : {amt:.0f}')
        lines.append("```")
        lines.append("")

    lines.extend(["## P&L по месяцам", ""])
    if pl:
        lines.append("| Месяц | Расход | Доход | Маржа | Накопит. |")
        lines.append("|-------|--------|-------|-------|----------|")
        for r in pl:
            lines.append(
                f"| {r['month']} | {r['expense_rub']:,.0f} | {r['income_total_rub']:,.0f} | "
                f"{r['margin_rub']:,.0f} | {r['cumulative_margin_rub']:,.0f} |"
            )
        lines.append("")
        if len(pl) >= 2:
            months = [r["month"] for r in pl]
            margins = [r["margin_rub"] for r in pl]
            lines.append("```mermaid")
            lines.append("xychart-beta")
            lines.append('    title "Маржа по месяцам (₽)"')
            lines.append("    x-axis [" + ", ".join(f'"{m}"' for m in months) + "]")
            mx = max(abs(x) for x in margins) or 1000
            lines.append(f'    y-axis "₽" {-mx:.0f} --> {mx:.0f}')
            lines.append("    bar [" + ", ".join(str(int(x)) for x in margins) + "]")
            lines.append("```")
            lines.append("")
    else:
        lines.append("_Нет данных P&L — добавьте строки в ledger или дашборд._")
        lines.append("")

    lines.extend(["## Бюджет-потолки (из бизнес-плана)", ""])
    lines.extend(
        [
            "| Режим | ₽/мес | Статус |",
            "|-------|-------|--------|",
            "| Минимальный | ~4 700–5 000 | ",
            f"| Факт расход YTD / мес | ~{ytd.get('expense_ytd_rub', 0) / max(1, datetime.now().month):,.0f} | сверка |",
            "| Рабочий | ~7 000 | цель фазы 1–3 |",
            "| Потолок LLM+API | 3 000 (+ VPS отдельно) | |",
            "",
        ]
    )

    lines.extend(["## Журнал ledger (последние 20)", ""])
    if ledger:
        lines.append("| Дата | Тип | Категория | ₽ | Примечание |")
        lines.append("|------|-----|-----------|---|------------|")
        for e in sorted(ledger, key=lambda x: x.get("date") or "", reverse=True)[:20]:
            note = (e.get("note") or e.get("vendor") or "")[:40]
            lines.append(
                f"| {e.get('date','')} | {e.get('type','')} | {e.get('category','')} | "
                f"{float(e.get('amount_rub') or 0):,.0f} | {note} |"
            )
        lines.append("")
    else:
        lines.append("_Пусто — первая строка: VPS в дашборде P&L._")
        lines.append("")

    lines.extend(["## KPI недели (все линии)", ""])
    if kpi_rows:
        lines.append("| Неделя | Garden ВК | Gdepar sess | Pension TG | Выручка | Заметки |")
        lines.append("|--------|-----------|-------------|------------|---------|---------|")
        for r in sorted(kpi_rows, key=lambda x: x.get("week") or "")[-12:]:
            lines.append(
                f"| {r.get('week','')} | {r.get('garden_vk_subs','')} | {r.get('gdepar_sessions','')} | "
                f"{r.get('pension_tg_subs','')} | {r.get('revenue_rub','')} | {(r.get('notes') or '')[:30]} |"
            )
        lines.append("")
        if len(kpi_rows) >= 2:
            weeks = [str(r.get("week", ""))[:10] for r in kpi_rows[-8:]]
            revs = [float(r.get("revenue_rub") or 0) for r in kpi_rows[-8:]]
            lines.append("```mermaid")
            lines.append("xychart-beta")
            lines.append('    title "Выручка по неделям (₽)"')
            lines.append("    x-axis [" + ", ".join(f'"{w}"' for w in weeks) + "]")
            mx = max(revs) or 100
            lines.append(f'    y-axis "₽" 0 --> {mx * 1.2:.0f}')
            lines.append("    line [" + ", ".join(str(int(x)) for x in revs) + "]")
            lines.append("```")
            lines.append("")
    else:
        lines.append("_Нет строк — воскресенье: дашборд → KPI недели → Сохранить._")
        lines.append("")

    if pen_rows:
        lines.extend(["## Pension KPI (отдельный файл)", ""])
        lines.append("| Неделя | TG | Сессии | /book | Orders |")
        lines.append("|--------|-----|--------|-------|--------|")
        for r in sorted(pen_rows, key=lambda x: x.get("week") or "")[-8:]:
            lines.append(
                f"| {r.get('week','')} | {r.get('tg_subs', r.get('pension_tg_subs',''))} | "
                f"{r.get('site_sessions','')} | {r.get('book_toc','')} | {r.get('orders','')} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Что сделать вручную",
            "",
            "- [ ] Воскресенье: KPI в дашборде → обновить `--finance`",
            "- [ ] Расходы недели в ledger (Cursor, OpenRouter)",
            "- [ ] Сверить §6.2 бизнес-плана: зелёный/красный по каналам",
            "",
        ]
    )

    (FINANCE_DIR / "00-СВОДКА.md").write_text("\n".join(lines), encoding="utf-8")

    checklist = _build_business_checklist(ledger, kpi_rows, pen_path.is_file())
    (FINANCE_DIR / "чеклист-бизнес-плана.md").write_text(checklist, encoding="utf-8")

    (FINANCE_DIR / "README.md").write_text(
        "\n".join(
            [
                "# Финансы (auto-sync)",
                "",
                "| Файл |",
                "|------|",
                "| [[00-СВОДКА]] — расходы, доходы, KPI, графики |",
                "| [[чеклист-бизнес-плана]] — §9 бизнес-плана + статус |",
                "",
                "`./venv/bin/python scripts/sync_empire_obsidian.py --finance`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"finance: → {FINANCE_DIR}")


def _build_business_checklist(ledger: list, kpi_rows: list, has_pension_kpi: bool) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    has_ledger = len(ledger) > 0
    has_kpi = len(kpi_rows) > 0

    def box(done: bool) -> str:
        return "x" if done else " "

    return f"""---
tags:
  - empire/finance
  - empire/checklist
do_not_import: true
synced_at: {ts}
---

# Чеклист «бизнес-план заведён»

> §9 `docs/empire_business_plan_2026.md` · авто-статус обновляется при `--finance`  
> Галочки **вручную** сохраняются между sync (как в _canon).

## Авто-статус ({ts})

- [{box(has_ledger)}] `empire_finance_ledger.json` не пуст
- [{box(has_kpi)}] `empire_weekly_kpi.json` — есть хотя бы одна неделя
- [{box(has_pension_kpi)}] `pension_weekly_metrics.json` заведён

## Вручную (отмечайте здесь)

- [ ] В «Мой налог» категория под инфопродукты
- [ ] Таблица §6.2 — первая строка (дашборд или Sheets)
- [ ] `YANDEX_METRIKA_ID` gdepar + pension
- [ ] Stern: дата 3 уроков → YooKassa
- [ ] Календарь: еженедельный обзор §7.1

## Регламент

| Когда | Действие |
|-------|----------|
| Воскресенье | KPI дашборд + [[00-СВОДКА]] + review |
| 1-е число | P&L месяц, НПД лимит |
| После sync | Открыть [[../_canon/business-plan-2026|business-plan]] §7 |

"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Empire docs/finance → Obsidian")
    ap.add_argument("--docs", action="store_true", help="Sync docs/ → Empire/_canon/")
    ap.add_argument("--finance", action="store_true", help="Generate Empire/_finance/")
    ap.add_argument("--all", action="store_true", help="Both")
    args = ap.parse_args()
    if not (args.docs or args.finance or args.all):
        args.all = True
    if args.all or args.docs:
        sync_docs()
    if args.all or args.finance:
        sync_finance()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
