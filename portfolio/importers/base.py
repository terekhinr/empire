"""Общие утилиты импорта брокерских отчётов."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import pandas as pd


DATE_COLS = ("дата", "date", "дата сделки", "дата операции", "дата заключения")
TICKER_COLS = ("тикер", "ticker", "код", "isin", "isin код", "ценная бумага", "инструмент", "актив")
QTY_COLS = ("количество", "кол-во", "qty", "quantity", "объем", "объём")
PRICE_COLS = ("цена", "price", "цена сделки", "цена одной")
AMOUNT_COLS = ("сумма", "amount", "объем сделки", "объём сделки", "сумма сделки")
TYPE_COLS = ("тип", "операция", "тип операции", "вид операции", "направление")


def _norm(s: Any) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _find_col(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    norm_map = {_norm(c): c for c in columns}
    for cand in candidates:
        for ncol, orig in norm_map.items():
            if cand in ncol:
                return orig
    return None


def parse_excel_table(path: str, sheet_name: str | int | None = 0) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")


def discover_trade_sheet(path: str) -> tuple[str | int, pd.DataFrame]:
    """Ищет лист со сделками по заголовкам."""
    xl = pd.ExcelFile(path, engine="openpyxl")
    for name in xl.sheet_names:
        raw = pd.read_excel(path, sheet_name=name, header=None, engine="openpyxl")
        for header_row in range(min(15, len(raw))):
            row = [_norm(x) for x in raw.iloc[header_row].tolist()]
            if any("дата" in c for c in row) and any(
                "кол" in c or "тикер" in c or "инструмент" in c or "ценн" in c for c in row
            ):
                df = pd.read_excel(path, sheet_name=name, header=header_row, engine="openpyxl")
                df = df.dropna(how="all")
                if len(df.columns) >= 4:
                    return name, df
    return 0, parse_excel_table(path, 0)


def parse_trade_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    cols = [str(c) for c in df.columns]
    c_date = _find_col(cols, DATE_COLS)
    c_ticker = _find_col(cols, TICKER_COLS)
    c_qty = _find_col(cols, QTY_COLS)
    c_price = _find_col(cols, PRICE_COLS)
    c_amount = _find_col(cols, AMOUNT_COLS)
    c_type = _find_col(cols, TYPE_COLS)
    if not c_date or not c_ticker:
        return []

    rows: list[dict[str, Any]] = []
    for _, r in df.iterrows():
        d = _parse_date(r.get(c_date))
        if not d:
            continue
        ticker = _extract_ticker(r.get(c_ticker))
        if not ticker:
            continue
        qty = _to_float(r.get(c_qty)) if c_qty else None
        price = _to_float(r.get(c_price)) if c_price else None
        amount = _to_float(r.get(c_amount)) if c_amount else None
        tx_type = _map_tx_type(r.get(c_type) if c_type else None, qty)
        if qty is None and amount and price:
            qty = amount / price
        if qty is None or qty == 0:
            continue
        rows.append(
            {
                "tx_date": d.isoformat(),
                "ticker": ticker,
                "quantity": abs(qty),
                "price": price,
                "amount": amount,
                "tx_type": tx_type,
                "note": _norm(r.get(c_type)) if c_type else "",
            }
        )
    return rows


def _parse_date(val: Any) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(" ", "").replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def _extract_ticker(val: Any) -> str | None:
    s = str(val).strip().upper()
    if not s or s == "NAN":
        return None
    # SBER, SBERP, SU26238RMFS4
    m = re.search(r"\b([A-Z]{2,12}\d{0,4}[A-Z]?)\b", s)
    if m:
        return m.group(1)
    m = re.search(r"\b(RU[A-Z0-9]{9,12})\b", s)
    if m:
        return m.group(1)
    if len(s) <= 16 and re.match(r"^[A-Z0-9._-]+$", s):
        return s.split()[0]
    return None


def _map_tx_type(raw: Any, qty: float | None) -> str:
    s = _norm(raw)
    if any(x in s for x in ("продаж", "sell", "выбыт")):
        return "sell"
    if any(x in s for x in ("покуп", "buy", "приобрет")):
        return "buy"
    if any(x in s for x in ("дивид", "купон")):
        return "dividend_reinvest"
    if qty is not None and qty < 0:
        return "sell"
    return "buy"
