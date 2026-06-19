"""Импорт брокерского отчёта ВТБ (XLSX)."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from portfolio.asset_classify import classify_asset
from portfolio.db import ensure_account, insert_cashflow, insert_transaction, upsert_instrument, upsert_manual_position
from portfolio.importers.isin_ticker import isin_to_ticker


def _parse_date(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()[:19]
    try:
        return pd.to_datetime(s).date().isoformat()
    except Exception:
        return None


def _extract_instrument(cell: Any) -> tuple[str | None, str | None, str | None]:
    s = str(cell or "").strip()
    if not s or s == "nan":
        return None, None, None
    if re.match(r"^[A-Z0-9_]{2,16}$", s) and "RU" not in s:
        return s, None, s
    m = re.search(r"(RU[A-Z0-9]{9,12})", s)
    isin = m.group(1) if m else None
    name = s.split(",")[0].strip() if "," in s else s
    ticker = None
    if isin:
        ticker = isin_to_ticker(isin)
    if not ticker and name:
        parts = name.split()
        if parts:
            ticker = parts[0].upper() if parts[0].isalpha() else name[:12]
    return ticker, isin, name


def _parse_vtb_label(blob: str) -> str:
    for pat in (
        r"№\s*субсчета[:\s]*([A-Z0-9]{5,8})",
        r"Соглашения\s+([A-Z0-9]{5,8})",
        r"субпозиция\s*№\s*([A-Z0-9]{5,8})",
    ):
        m = re.search(pat, blob, re.I)
        if m:
            return m.group(1).upper()
    return "Основной"


def _parse_vtb_price(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(str(val).replace(",", "").replace(" ", ""))
    except (TypeError, ValueError):
        return None


def _resolve_vtb_account_id(conn: sqlite3.Connection, label: str) -> int:
    """Один субсчёт ВТБ: переименовываем «Отчет» → 126M85, убираем дубликаты."""
    broker_row = conn.execute("SELECT id FROM brokers WHERE code='vtb'").fetchone()
    if not broker_row:
        return ensure_account(conn, "vtb", label=label)
    broker_id = broker_row["id"]
    accounts = conn.execute(
        "SELECT id, label FROM accounts WHERE broker_id=? ORDER BY id", (broker_id,)
    ).fetchall()

    primary_id: int | None = None
    for a in accounts:
        tx_n = conn.execute(
            "SELECT COUNT(*) AS c FROM transactions WHERE account_id=?", (a["id"],)
        ).fetchone()["c"]
        if tx_n > 0:
            primary_id = int(a["id"])
            break

    if primary_id is None:
        return ensure_account(conn, "vtb", label=label)

    if primary_id is None:
        return ensure_account(conn, "vtb", label=label)

    for a in accounts:
        aid = int(a["id"])
        if aid == primary_id:
            continue
        mp = conn.execute(
            "SELECT COUNT(*) AS c FROM manual_positions WHERE account_id=?", (aid,)
        ).fetchone()["c"]
        if mp:
            for row in conn.execute(
                "SELECT instrument_id, quantity, avg_price, note FROM manual_positions WHERE account_id=?",
                (aid,),
            ):
                upsert_manual_position(
                    conn,
                    account_id=primary_id,
                    instrument_id=int(row["instrument_id"]),
                    quantity=float(row["quantity"]),
                    avg_price=float(row["avg_price"]) if row["avg_price"] is not None else None,
                    note=row["note"],
                )
            conn.execute("DELETE FROM manual_positions WHERE account_id=?", (aid,))
        for table in ("cashflows", "transactions"):
            conn.execute(
                f"UPDATE {table} SET account_id=? WHERE account_id=?",
                (primary_id, aid),
            )
        conn.execute("DELETE FROM accounts WHERE id=?", (aid,))
    conn.execute("UPDATE accounts SET label=? WHERE id=?", (label, primary_id))
    return primary_id


def import_vtb_balances(conn: sqlite3.Connection, path: str | Path) -> dict[str, Any]:
    """Исходящие остатки ЦБ из отчёта → manual_positions (приоритет над сделками)."""
    path = Path(path)
    raw = pd.read_excel(path, sheet_name=0, header=None, engine="openpyxl")
    blob = " ".join(str(x) for x in raw.iloc[:12].values.flatten() if str(x) != "nan")
    label = _parse_vtb_label(blob)
    account_id = _resolve_vtb_account_id(conn, label)
    conn.execute(
        "DELETE FROM manual_positions WHERE account_id=? AND note LIKE 'snapshot:vtb:%'",
        (account_id,),
    )

    updated = 0
    report_total = None
    in_section = False
    for i in range(len(raw)):
        row = " ".join(str(x) for x in raw.iloc[i].tolist() if str(x) != "nan")
        if "Отчёт об остатках ценных бумаг" in row:
            in_section = True
            continue
        if not in_section:
            continue
        if "Движение ценных бумаг" in row:
            break
        cells = [str(x).strip() for x in raw.iloc[i].tolist() if str(x) != "nan"]
        if not cells:
            continue
        if cells[0].startswith("ИТОГО"):
            for c in cells[1:]:
                p = _parse_vtb_price(c)
                if p is not None:
                    report_total = p
                    break
            break
        if cells[0] in ("АКЦИЯ", "ПАЙ", "ОБЛИГАЦИЯ"):
            continue
        m = re.search(r"(RU[A-Z0-9]{9,12})", cells[0])
        if not m:
            continue
        isin = m.group(1)
        try:
            qty = float(str(cells[4]).replace(",", "").replace(" ", ""))
        except (IndexError, ValueError):
            continue
        if qty <= 0:
            continue
        price = _parse_vtb_price(cells[7]) if len(cells) > 7 else None
        name = cells[0].split(",")[0].strip()
        ticker = isin_to_ticker(isin) or isin
        asset_class, is_liq = classify_asset(ticker, name=name)
        iid = upsert_instrument(
            conn, ticker, isin=isin, name=name[:200], asset_class=asset_class, is_liquidity_fund=is_liq
        )
        upsert_manual_position(
            conn,
            account_id=account_id,
            instrument_id=iid,
            quantity=qty,
            avg_price=price,
            note=f"snapshot:vtb:{label}:{path.name}",
        )
        if price:
            from datetime import date

            period_end = _report_period_end(blob) or date.today().isoformat()
            today = date.today().isoformat()
            for px_date in (period_end, today):
                conn.execute(
                    """
                    INSERT INTO price_cache (ticker, price_date, price, source)
                    VALUES (?, ?, ?, 'vtb_report')
                    ON CONFLICT(ticker, price_date) DO UPDATE SET price=excluded.price, source=excluded.source
                    """,
                    (ticker, px_date, price),
                )
        updated += 1

    return {"broker": "vtb", "account": label, "positions_updated": updated, "report_total": report_total}


def _report_period_end(blob: str) -> str | None:
    m = re.search(r"по\s+(\d{2}\.\d{2}\.\d{4})", blob)
    if not m:
        return None
    from datetime import datetime

    try:
        return datetime.strptime(m.group(1), "%d.%m.%Y").date().isoformat()
    except ValueError:
        return None


def _import_vtb_cashflows(
    conn: sqlite3.Connection, path: Path, account_id: int, label: str
) -> int:
    raw = pd.read_excel(path, sheet_name=0, header=None, engine="openpyxl")
    added = 0
    in_section = False
    for i in range(len(raw)):
        cells = raw.iloc[i].tolist()
        row_txt = " ".join(str(x) for x in cells if str(x) != "nan").strip()
        if row_txt == "Движение денежных средств":
            in_section = True
            continue
        if in_section and any(
            x in row_txt for x in ("Движение ценных бумаг", "Отчёт об остатках", "ИТОГО по")
        ):
            break
        if not in_section:
            continue
        if len(cells) < 10 or not pd.notna(cells[1]):
            continue
        if str(cells[1]).lower() in ("дата", "основной рынок"):
            continue
        tx_date = _parse_date(cells[1])
        if not tx_date:
            continue
        try:
            amount = float(cells[2])
        except (TypeError, ValueError):
            continue
        op = str(cells[9]).lower() if pd.notna(cells[9]) else ""
        comment = str(cells[15])[:120] if len(cells) > 15 and pd.notna(cells[15]) else ""
        if "зачисление денежных" in op:
            flow_type = "deposit"
        elif "списание денежных" in op:
            flow_type = "withdrawal"
        else:
            continue
        amt = abs(amount)
        if amt <= 0:
            continue
        ext = f"vtb:cf:{label}:{tx_date}:{amt:.2f}:{flow_type}"
        if insert_cashflow(
            conn,
            account_id=account_id,
            flow_date=tx_date,
            amount=amt,
            flow_type=flow_type,
            note=comment or None,
            external_id=ext,
        ):
            added += 1
    return added


def import_vtb_report(conn: sqlite3.Connection, path: str | Path) -> dict[str, Any]:
    path = Path(path)
    raw = pd.read_excel(path, sheet_name=0, header=None, engine="openpyxl")
    blob = " ".join(str(x) for x in raw.iloc[:12].values.flatten() if str(x) != "nan")
    label = _parse_vtb_label(blob)
    account_id = _resolve_vtb_account_id(conn, label)

    added = skipped = 0
    header_rows: list[int] = []
    for i in range(len(raw)):
        row = " ".join(str(x) for x in raw.iloc[i].tolist() if str(x) != "nan").lower()
        if "дата и время заключения сделки" in row and "вид сделки" in row:
            header_rows.append(i)

    for hi in header_rows:
        cols = [str(c).replace("\n", " ") for c in raw.iloc[hi].tolist()]
        for ri in range(hi + 1, len(raw)):
            row = raw.iloc[ri]
            inst_cell = row.iloc[1] if len(row) > 1 else None
            if pd.isna(inst_cell):
                continue
            inst_str = str(inst_cell).strip()
            if not inst_str or inst_str == "nan":
                continue
            if "наименование" in inst_str.lower() or "финансовый инструмент" in inst_str.lower():
                break

            date_cell = row.iloc[2] if len(row) > 2 else None
            tx_date = _parse_date(date_cell)
            if not tx_date:
                continue

            # find columns by header
            type_idx = next((i for i, c in enumerate(cols) if "вид сделки" in c.lower()), 5)
            qty_idx = next((i for i, c in enumerate(cols) if "количество" in c.lower()), 7)
            price_idx = next((i for i, c in enumerate(cols) if c.lower().startswith("цена")), 9)
            amount_idx = next(
                (i for i, c in enumerate(cols) if "сумма сделки" in c.lower()),
                11,
            )
            deal_idx = next((i for i, c in enumerate(cols) if "№ сделки" in c.lower()), 25)

            tx_type_raw = str(row.iloc[type_idx] if type_idx < len(row) else "").lower()
            tx_type = "sell" if "продаж" in tx_type_raw else "buy"
            try:
                qty = abs(float(row.iloc[qty_idx]))
            except (TypeError, ValueError):
                continue
            if qty <= 0:
                continue
            try:
                price = float(row.iloc[price_idx])
            except (TypeError, ValueError):
                price = None
            try:
                amount = abs(float(row.iloc[amount_idx]))
            except (TypeError, ValueError):
                amount = None

            ticker, isin, name = _extract_instrument(inst_cell)
            if not ticker:
                continue
            asset_class, is_liq = classify_asset(ticker, name=name)
            deal = str(row.iloc[deal_idx] if deal_idx < len(row) else ri).replace("\n", "")[:30]
            iid = upsert_instrument(
                conn,
                ticker,
                isin=isin,
                name=name,
                asset_class=asset_class,
                is_liquidity_fund=is_liq,
            )
            ok = insert_transaction(
                conn,
                account_id=account_id,
                instrument_id=iid,
                tx_date=tx_date,
                tx_type=tx_type,
                quantity=qty,
                price=price,
                amount=amount,
                external_id=f"vtb:{label}:{deal}:{tx_date}:{ticker}:{tx_type}",
                note=name,
            )
            if ok:
                added += 1
            else:
                skipped += 1

    balances = import_vtb_balances(conn, path)
    cf_added = _import_vtb_cashflows(conn, path, account_id, label)
    return {
        "broker": "vtb",
        "account": label,
        "added": added,
        "skipped": skipped,
        "cashflows": cf_added,
        "balances": balances,
    }
