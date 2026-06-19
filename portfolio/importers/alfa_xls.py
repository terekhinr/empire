"""Импорт брокерского отчёта Альфа-Инвестиции (нативный XLS)."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from portfolio.db import ensure_account, insert_cashflow, insert_transaction, upsert_instrument, upsert_manual_position
from portfolio.asset_classify import classify_asset
from portfolio.importers.isin_ticker import isin_to_ticker


def _parse_agreement(path: Path) -> str:
    raw = pd.read_excel(path, sheet_name=0, header=None, nrows=8, engine="xlrd")
    blob = " ".join(str(x) for x in raw.values.flatten() if str(x) != "nan")
    m = re.search(r"№\s*(\d+)", blob)
    return m.group(1) if m else "Основной"


def _parse_date(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip().split("\n")[0][:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def import_alfa_report(conn: sqlite3.Connection, path: str | Path) -> dict[str, Any]:
    path = Path(path)
    agreement = _parse_agreement(path)
    account_id = ensure_account(conn, "alfa", label=agreement)

    df = pd.read_excel(path, sheet_name="Завершенные сделки", header=14, engine="xlrd")
    qcol = "Количество актива⁷,\nшт./грамм"
    added = skipped = 0
    for _, r in df.iterrows():
        isin = str(r.get("ISIN/рег.код", "")).strip()
        if not isin or isin == "nan":
            continue
        qty = float(r.get(qcol, 0) or 0)
        if qty == 0:
            continue
        tx_type = "sell" if qty < 0 else "buy"
        qty = abs(qty)
        price = float(r.get("Цена", 0) or 0)
        amount = float(r.get("Сумма сделки \nв валюте расчетов⁸", 0) or 0)
        tx_date = _parse_date(r.get("Дата\nзаключен."))
        if not tx_date:
            continue
        ticker = isin_to_ticker(isin) or isin
        name = str(r.get("Актив", "")).strip() or None
        deal = str(r.get("№ сделки", "")).replace("\n", "_")[:40]
        asset_class, is_liq = classify_asset(ticker, name=name)
        iid = upsert_instrument(
            conn, ticker, isin=isin, name=name, asset_class=asset_class, is_liquidity_fund=is_liq
        )
        ok = insert_transaction(
            conn,
            account_id=account_id,
            instrument_id=iid,
            tx_date=tx_date,
            tx_type=tx_type,
            quantity=qty,
            price=price or None,
            amount=abs(amount) or None,
            external_id=f"alfa:{agreement}:{deal}",
            note=name,
        )
        if ok:
            added += 1
        else:
            skipped += 1

    cf_added = _import_cashflows(conn, path, account_id, agreement)
    snap = import_alfa_snapshot(conn, path)
    return {
        "broker": "alfa",
        "account": agreement,
        "parsed": len(df),
        "added": added,
        "skipped": skipped,
        "cashflows": cf_added,
        "snapshot": snap,
    }


def import_alfa_snapshot(conn: sqlite3.Connection, path: str | Path) -> dict[str, Any]:
    """Остатки на конец периода из листа «Динамика позиций» → manual_positions."""
    path = Path(path)
    agreement = _parse_agreement(path)
    account_id = ensure_account(conn, "alfa", label=agreement)
    conn.execute(
        "DELETE FROM manual_positions WHERE account_id=? AND note LIKE 'snapshot:alfa:%'",
        (account_id,),
    )

    raw = pd.read_excel(path, sheet_name="Динамика позиций", header=None, engine="xlrd")
    skip_names = {
        "Актив ¹",
        "RUB",
        "На начало периода",
        "На конец периода",
        "Акции",
        "Паи",
        "Паи ",
        "Облигации",
        "Драг. металлы",
        "Фонды",
        "Валюта",
    }
    updated = 0
    i = 0
    while i < len(raw) - 1:
        name_cell = raw.iloc[i, 6]
        if pd.isna(name_cell):
            i += 1
            continue
        name = str(name_cell).strip()
        if not name or name in skip_names or name.startswith("¹") or "Динамика" in name:
            i += 1
            continue
        isin_raw = raw.iloc[i + 1, 6]
        isin = str(isin_raw).strip() if pd.notna(isin_raw) else ""
        if not re.match(r"^RU[A-Z0-9]{9,12}$", isin):
            i += 1
            continue
        try:
            qty = float(raw.iloc[i, 15])
            value = float(raw.iloc[i, 17])
        except (TypeError, ValueError):
            i += 2
            continue
        if qty <= 0 or pd.isna(qty) or pd.isna(value):
            i += 2
            continue
        ticker = isin_to_ticker(isin) or isin
        avg_price = value / qty if qty else None
        asset_class, is_liq = classify_asset(ticker, name=name)
        iid = upsert_instrument(
            conn, ticker, isin=isin, name=name[:200], asset_class=asset_class, is_liquidity_fund=is_liq
        )
        upsert_manual_position(
            conn,
            account_id=account_id,
            instrument_id=iid,
            quantity=qty,
            avg_price=avg_price,
            note=f"snapshot:alfa:{agreement}:{path.name}",
        )
        updated += 1
        i += 2

    return {"account": agreement, "positions_updated": updated}


def _alfa_transfer_kind(comment: str, amount: float) -> str | None:
    """Пополнение/вывод по строке «Перевод» (не дивиденды, купоны, НДФЛ)."""
    cl = comment.strip().lower()
    if any(
        k in cl
        for k in (
            "дивид",
            "купон",
            "погашен",
            "ндфл",
            "возврат налог",
            "доход",
            "див.",
            "выплата по поручению",
        )
    ):
        return None
    if amount <= 0:
        return None
    if cl.startswith("из ") or "перевод денежных средств из" in cl or "из ао" in cl:
        return "deposit"
    if cl.startswith("в ") or "вывод" in cl or "списан" in cl:
        return "withdrawal"
    return None


def _alfa_flow_date(row: pd.Series) -> str | None:
    for idx in (2, 6):
        if len(row) > idx:
            d = _parse_date(row.iloc[idx])
            if d:
                return d
    return None


def _import_cashflows(
    conn: sqlite3.Connection, path: Path, account_id: int, agreement: str
) -> int:
    raw = pd.read_excel(path, sheet_name=" Движение ДС", header=None, engine="xlrd")
    added = 0
    for _, r in raw.iterrows():
        op = str(r.iloc[9] if len(r) > 9 else "").strip()
        if op != "Перевод":
            continue
        comment = str(r.iloc[10] if len(r) > 10 else "").strip()
        try:
            amt = float(r.iloc[14])
        except (TypeError, ValueError):
            continue
        flow_type = _alfa_transfer_kind(comment, amt)
        if not flow_type:
            continue
        d = _alfa_flow_date(r)
        if not d:
            continue
        note = comment[:120] or None
        ext = f"alfa:cf:{agreement}:{d}:{amt:.2f}:{flow_type}:{hash(comment) & 0xFFFFFF:06x}"
        if insert_cashflow(
            conn,
            account_id=account_id,
            flow_date=d,
            amount=abs(amt),
            flow_type=flow_type,
            note=note,
            external_id=ext,
        ):
            added += 1
    return added
