"""Тесты finance_ledger.py."""

from finance_ledger import (
    append_ledger_entry,
    build_pl_monthly,
    kpi_template_csv,
    ledger_totals_by_month,
    load_ledger,
    save_ledger,
    ytd_totals,
)


def test_append_and_monthly(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.json"
    monkeypatch.setenv("EMPIRE_FINANCE_LEDGER", str(ledger))
    append_ledger_entry(
        {
            "date": "2026-05-01",
            "type": "expense",
            "category": "vps",
            "amount_rub": 2373,
            "note": "VPS",
        }
    )
    append_ledger_entry(
        {
            "date": "2026-05-15",
            "type": "income",
            "category": "manual",
            "amount_rub": 390,
            "persona": "stern",
        }
    )
    entries = load_ledger(ledger)
    assert len(entries) == 2
    m = ledger_totals_by_month(entries)
    assert m["2026-05"]["expense"] == 2373
    assert m["2026-05"]["income"] == 390
    pl = build_pl_monthly()
    assert any(r["month"] == "2026-05" for r in pl)
    assert pl[-1]["margin_rub"] == 390 - 2373


def test_kpi_template_has_header():
    csv = kpi_template_csv()
    assert "week" in csv.splitlines()[0]
    assert "cursor_spend_rub" in csv
    assert "openrouter_spend_rub" in csv
    assert "fal_spend_rub" in csv
    assert "garden_vk_subs" in csv


def test_save_weekly_kpi_llm_sum(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_WEEKLY_KPI_JSON", str(tmp_path / "kpi.json"))
    from finance_ledger import load_weekly_kpi, save_weekly_kpi_row

    save_weekly_kpi_row(
        {
            "week": "2026-05-26",
            "cursor_spend_rub": 100,
            "openrouter_spend_rub": 200,
            "fal_spend_rub": 50,
        }
    )
    rows = load_weekly_kpi()
    assert rows[0]["llm_spend_rub"] == 350


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "l.json"
    save_ledger([{"date": "2026-01-01", "type": "expense", "amount_rub": 100}], p)
    assert len(load_ledger(p)) == 1


def test_ytd_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_FINANCE_LEDGER", str(tmp_path / "empty.json"))
    t = ytd_totals()
    assert "expense_ytd_rub" in t
    assert t["income_sales_ytd_rub"] == 0.0
