"""Учёт расходов/доходов Empire: ledger JSON + агрегация с sales.db."""

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent


def _ledger_path(path: Path | None = None) -> Path:
    return path or Path(os.getenv("EMPIRE_FINANCE_LEDGER", str(BASE_DIR / "data" / "empire_finance_ledger.json")))


def _kpi_path(path: Path | None = None) -> Path:
    return path or Path(os.getenv("EMPIRE_WEEKLY_KPI_JSON", str(BASE_DIR / "data" / "empire_weekly_kpi.json")))


def _sales_path(path: Path | None = None) -> Path:
    return path or Path(os.getenv("EMPIRE_SALES_DB", str(BASE_DIR / "sales.db")))

EXPENSE_CATEGORIES = (
    "vps",
    "domain",
    "cursor",
    "openrouter",
    "fal",
    "llm",
    "ads",
    "proxy",
    "tax",
    "other",
)
AI_TOOL_CATEGORIES = ("cursor", "openrouter", "fal", "llm")

EXPENSE_CATEGORY_LABELS = {
    "vps": "VPS / хостинг",
    "domain": "Домены / DNS",
    "cursor": "Cursor IDE",
    "openrouter": "OpenRouter (LLM API)",
    "fal": "fal.ai (картинки Flux)",
    "llm": "LLM прочее",
    "ads": "Реклама",
    "proxy": "Прокси Telethon",
    "tax": "Налог НПД",
    "other": "Прочее",
}

INCOME_CATEGORIES = ("yookassa", "stars", "vk", "manual", "other")

KPI_COLUMNS = [
    "week",
    "empire_ok",
    "cursor_spend_rub",
    "openrouter_spend_rub",
    "fal_spend_rub",
    "llm_spend_rub",
    "garden_vk_subs",
    "gdepar_sessions",
    "stern_leads",
    "pension_tg_subs",
    "pension_site_sessions",
    "pension_book_toc",
    "pension_buy_clicks",
    "tg_posts_published",
    "autopost_failures",
    "gift_emails",
    "gdepar_phone_reveals",
    "orders",
    "revenue_rub",
    "expenses_rub",
    "top_utm",
    "notes",
]


def load_ledger(path: Path | None = None) -> list[dict]:
    p = _ledger_path(path)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_ledger(entries: list[dict], path: Path | None = None) -> None:
    p = _ledger_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_ledger_entry(entry: dict, path: Path | None = None) -> dict:
    """Добавить строку; нормализует date, type, amount."""
    row = dict(entry)
    row["date"] = (row.get("date") or date.today().isoformat())[:10]
    row["type"] = (row.get("type") or "expense").strip().lower()
    if row["type"] not in ("expense", "income"):
        raise ValueError("type must be expense or income")
    row["amount_rub"] = float(row.get("amount_rub") or 0)
    if row["amount_rub"] < 0:
        raise ValueError("amount_rub must be >= 0")
    row["category"] = (row.get("category") or "other").strip().lower()
    entries = load_ledger(path)
    entries.append(row)
    entries.sort(key=lambda e: (e.get("date") or "", e.get("type") or ""))
    save_ledger(entries, path)
    return row


def _month_key(iso_date: str) -> str:
    return (iso_date or "")[:7]


def ledger_totals_by_month(entries: list[dict] | None = None) -> dict[str, dict[str, float]]:
    """{ '2026-05': { 'expense': x, 'income': y, 'expense_vps': ... } }"""
    entries = entries if entries is not None else load_ledger()
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for e in entries:
        m = _month_key(str(e.get("date") or ""))
        if not m or len(m) < 7:
            continue
        t = e.get("type") or "expense"
        amt = float(e.get("amount_rub") or 0)
        out[m][t] += amt
        cat = e.get("category") or "other"
        out[m][f"{t}_{cat}"] += amt
    return {k: dict(v) for k, v in out.items()}


def sales_revenue_by_month(path: Path | None = None) -> dict[str, float]:
    """Оплаченные orders + donations по месяцам из sales.db."""
    p = _sales_path(path)
    if not p.is_file():
        return {}
    conn = sqlite3.connect(p)
    months: dict[str, float] = defaultdict(float)
    for table, status_filter in (
        ("orders", "status IN ('paid', 'completed')"),
        ("donations", "status = 'paid'"),
    ):
        try:
            rows = conn.execute(
                f"SELECT substr(created_at, 1, 7) AS ym, COALESCE(SUM(amount_rub), 0) "
                f"FROM {table} WHERE {status_filter} AND created_at IS NOT NULL "
                f"GROUP BY ym"
            ).fetchall()
            for ym, total in rows:
                if ym:
                    months[str(ym)] += float(total or 0)
        except sqlite3.OperationalError:
            pass
    conn.close()
    return dict(months)


def build_pl_monthly(months_back: int = 12) -> list[dict]:
    """Свод P&L по месяцам для дашборда и CSV."""
    ledger_m = ledger_totals_by_month()
    sales_m = sales_revenue_by_month()
    all_months = sorted(set(ledger_m) | set(sales_m), reverse=True)[:months_back]
    all_months.sort()
    rows: list[dict] = []
    cumulative = 0.0
    for ym in all_months:
        lm = ledger_m.get(ym, {})
        exp = float(lm.get("expense", 0))
        inc_ledger = float(lm.get("income", 0))
        inc_sales = float(sales_m.get(ym, 0))
        income_total = inc_ledger + inc_sales
        margin = income_total - exp
        cumulative += margin
        rows.append(
            {
                "month": ym,
                "expense_rub": round(exp, 2),
                "income_ledger_rub": round(inc_ledger, 2),
                "income_sales_rub": round(inc_sales, 2),
                "income_total_rub": round(income_total, 2),
                "margin_rub": round(margin, 2),
                "cumulative_margin_rub": round(cumulative, 2),
            }
        )
    return rows


def ledger_to_csv(entries: list[dict] | None = None) -> str:
    entries = entries if entries is not None else load_ledger()
    buf = io.StringIO()
    fields = [
        "date",
        "type",
        "category",
        "amount_rub",
        "vendor",
        "persona",
        "product_id",
        "source_id",
        "order_id",
        "note",
        "receipt_url",
    ]
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for e in sorted(entries, key=lambda x: x.get("date") or ""):
        w.writerow({k: e.get(k, "") for k in fields})
    return buf.getvalue()


def pl_to_csv(pl_rows: list[dict] | None = None) -> str:
    pl_rows = pl_rows if pl_rows is not None else build_pl_monthly()
    if not pl_rows:
        return "month,expense_rub,income_ledger_rub,income_sales_rub,income_total_rub,margin_rub,cumulative_margin_rub\n"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(pl_rows[0].keys()))
    w.writeheader()
    w.writerows(pl_rows)
    return buf.getvalue()


def load_weekly_kpi() -> list[dict]:
    p = _kpi_path()
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_weekly_kpi_row(row: dict) -> None:
    week = (row.get("week") or date.today().isoformat()).strip()
    row = {**row, "week": week}
    # Сводная строка для старых таблиц / графиков
    if "llm_spend_rub" not in row or row.get("llm_spend_rub") in (None, "", 0, 0.0):
        row["llm_spend_rub"] = (
            float(row.get("cursor_spend_rub") or 0)
            + float(row.get("openrouter_spend_rub") or 0)
            + float(row.get("fal_spend_rub") or 0)
        )
    rows = load_weekly_kpi()
    rows = [r for r in rows if (r.get("week") or "") != week]
    rows.append(row)
    rows.sort(key=lambda r: r.get("week") or "")
    kp = _kpi_path()
    kp.parent.mkdir(parents=True, exist_ok=True)
    kp.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def kpi_template_csv() -> str:
    """Шаблон для импорта в Google Sheets (§6.2 бизнес-плана)."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=KPI_COLUMNS)
    w.writeheader()
    w.writerow(
        {
            "week": date.today().isoformat(),
            "empire_ok": "1",
            "cursor_spend_rub": "0",
            "openrouter_spend_rub": "0",
            "fal_spend_rub": "0",
            "llm_spend_rub": "0",
            "garden_vk_subs": "0",
            "gdepar_sessions": "0",
            "stern_leads": "0",
            "pension_tg_subs": "0",
            "pension_site_sessions": "0",
            "pension_book_toc": "0",
            "pension_buy_clicks": "0",
            "orders": "0",
            "revenue_rub": "0",
            "expenses_rub": "2373",
            "top_utm": "",
            "notes": "пример строки — удалите после импорта",
        }
    )
    return buf.getvalue()


def expense_by_category(
    *,
    year: str | None = None,
    month: str | None = None,
    entries: list[dict] | None = None,
) -> dict[str, float]:
    """Суммы расходов по category за год (YYYY) или месяц (YYYY-MM)."""
    entries = entries if entries is not None else load_ledger()
    out: dict[str, float] = defaultdict(float)
    for e in entries:
        if e.get("type") != "expense":
            continue
        d = str(e.get("date") or "")
        if year and not d.startswith(year):
            continue
        if month and not d.startswith(month):
            continue
        cat = (e.get("category") or "other").lower()
        out[cat] += float(e.get("amount_rub") or 0)
    return dict(out)


def ytd_totals() -> dict[str, Any]:
    """Итоги с начала года для метрик дашборда."""
    year = str(date.today().year)
    entries = [e for e in load_ledger() if str(e.get("date", "")).startswith(year)]
    exp = sum(float(e.get("amount_rub") or 0) for e in entries if e.get("type") == "expense")
    by_cat = expense_by_category(year=year, entries=entries)
    ai_tools = sum(by_cat.get(c, 0) for c in AI_TOOL_CATEGORIES)
    inc_l = sum(float(e.get("amount_rub") or 0) for e in entries if e.get("type") == "income")
    sales_ytd = 0.0
    sp = _sales_path()
    if sp.is_file():
        conn = sqlite3.connect(sp)
        try:
            o = conn.execute(
                "SELECT COALESCE(SUM(amount_rub),0) FROM orders "
                "WHERE status IN ('paid','completed') AND created_at >= ?",
                (f"{year}-01-01",),
            ).fetchone()[0]
            d = conn.execute(
                "SELECT COALESCE(SUM(amount_rub),0) FROM donations "
                "WHERE status='paid' AND created_at >= ?",
                (f"{year}-01-01",),
            ).fetchone()[0]
            sales_ytd = float(o or 0) + float(d or 0)
        except sqlite3.OperationalError:
            pass
        conn.close()
    return {
        "year": year,
        "expense_ytd_rub": round(exp, 2),
        "expense_by_category": {k: round(v, 2) for k, v in by_cat.items()},
        "expense_cursor_ytd_rub": round(by_cat.get("cursor", 0), 2),
        "expense_openrouter_ytd_rub": round(by_cat.get("openrouter", 0), 2),
        "expense_fal_ytd_rub": round(by_cat.get("fal", 0), 2),
        "expense_ai_tools_ytd_rub": round(ai_tools, 2),
        "income_ledger_ytd_rub": round(inc_l, 2),
        "income_sales_ytd_rub": round(sales_ytd, 2),
        "income_total_ytd_rub": round(inc_l + sales_ytd, 2),
        "margin_ytd_rub": round(inc_l + sales_ytd - exp, 2),
    }
