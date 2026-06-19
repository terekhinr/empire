"""Расчёт позиций из сделок и ручных снимков."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass
class PositionRow:
    account_id: int
    account_label: str
    broker_code: str
    broker_name: str
    broker_mode: str
    instrument_id: int
    ticker: str
    instrument_name: str | None
    asset_class: str
    is_liquidity_fund: bool
    quantity: float
    avg_price: float | None
    source: str  # transactions | manual


def _positions_from_transactions(conn: sqlite3.Connection) -> dict[tuple[int, int], PositionRow]:
    rows = conn.execute(
        """
        SELECT
            t.account_id, a.label AS account_label,
            t.instrument_id, t.tx_type, t.quantity, t.price, t.amount,
            b.code AS broker_code, b.name AS broker_name, b.mode AS broker_mode,
            i.ticker, i.name AS instrument_name, i.asset_class, i.is_liquidity_fund
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        JOIN brokers b ON b.id = a.broker_id
        JOIN instruments i ON i.id = t.instrument_id
        WHERE t.instrument_id IS NOT NULL
        ORDER BY t.tx_date, t.id
        """
    ).fetchall()

    state: dict[tuple[int, int], dict[str, Any]] = {}
    for r in rows:
        key = (int(r["account_id"]), int(r["instrument_id"]))
        st = state.setdefault(
            key,
            {
                "qty": 0.0,
                "cost": 0.0,
                "broker_code": r["broker_code"],
                "broker_name": r["broker_name"],
                "broker_mode": r["broker_mode"],
                "account_label": r["account_label"],
                "ticker": r["ticker"],
                "instrument_name": r["instrument_name"],
                "asset_class": r["asset_class"],
                "is_liquidity_fund": bool(r["is_liquidity_fund"]),
            },
        )
        q = float(r["quantity"] or 0)
        price = float(r["price"] or 0)
        tx_type = r["tx_type"]
        if tx_type in ("buy", "dividend_reinvest"):
            st["qty"] += q
            st["cost"] += q * price if price else float(r["amount"] or 0)
        elif tx_type == "sell":
            if st["qty"] > 0:
                avg = st["cost"] / st["qty"] if st["qty"] else 0
                st["qty"] -= q
                st["cost"] -= avg * q
                if st["qty"] <= 1e-9:
                    st["qty"] = 0.0
                    st["cost"] = 0.0

    out: dict[tuple[int, int], PositionRow] = {}
    for (account_id, instrument_id), st in state.items():
        if st["qty"] <= 1e-9:
            continue
        avg = st["cost"] / st["qty"] if st["qty"] else None
        out[(account_id, instrument_id)] = PositionRow(
            account_id=account_id,
            account_label=st.get("account_label", ""),
            broker_code=st["broker_code"],
            broker_name=st["broker_name"],
            broker_mode=st["broker_mode"],
            instrument_id=instrument_id,
            ticker=st["ticker"],
            instrument_name=st["instrument_name"],
            asset_class=st["asset_class"],
            is_liquidity_fund=st["is_liquidity_fund"],
            quantity=st["qty"],
            avg_price=avg,
            source="transactions",
        )
    return out


def _positions_from_manual(conn: sqlite3.Connection) -> dict[tuple[int, int], PositionRow]:
    rows = conn.execute(
        """
        SELECT
            mp.account_id, a.label AS account_label, mp.instrument_id, mp.quantity, mp.avg_price,
            b.code AS broker_code, b.name AS broker_name, b.mode AS broker_mode,
            i.ticker, i.name AS instrument_name, i.asset_class, i.is_liquidity_fund
        FROM manual_positions mp
        JOIN accounts a ON a.id = mp.account_id
        JOIN brokers b ON b.id = a.broker_id
        JOIN instruments i ON i.id = mp.instrument_id
        WHERE mp.quantity > 0
        """
    ).fetchall()
    out: dict[tuple[int, int], PositionRow] = {}
    for r in rows:
        key = (int(r["account_id"]), int(r["instrument_id"]))
        out[key] = PositionRow(
            account_id=int(r["account_id"]),
            account_label=r["account_label"] or "",
            broker_code=r["broker_code"],
            broker_name=r["broker_name"],
            broker_mode=r["broker_mode"],
            instrument_id=int(r["instrument_id"]),
            ticker=r["ticker"],
            instrument_name=r["instrument_name"],
            asset_class=r["asset_class"],
            is_liquidity_fund=bool(r["is_liquidity_fund"]),
            quantity=float(r["quantity"]),
            avg_price=float(r["avg_price"]) if r["avg_price"] is not None else None,
            source="manual",
        )
    return out


def compute_positions(conn: sqlite3.Connection) -> list[PositionRow]:
    """Объединяет сделки и ручные позиции; manual перекрывает transactions для того же ключа."""
    tx_pos = _positions_from_transactions(conn)
    manual_pos = _positions_from_manual(conn)
    merged = {**tx_pos, **manual_pos}
    return sorted(merged.values(), key=lambda p: (p.broker_code, p.ticker))


def enrich_with_prices(
    positions: list[PositionRow],
    prices: dict[str, float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in positions:
        last = prices.get(p.ticker)
        market_value = (last * p.quantity) if last is not None else None
        cost = (p.avg_price * p.quantity) if p.avg_price is not None else None
        pnl = (market_value - cost) if market_value is not None and cost is not None else None
        pnl_pct = ((pnl / cost) * 100) if pnl is not None and cost and cost > 0 else None
        rows.append(
            {
                "broker": p.broker_name,
                "broker_code": p.broker_code,
                "account_id": p.account_id,
                "account_label": p.account_label,
                "broker_mode": p.broker_mode,
                "ticker": p.ticker,
                "name": p.instrument_name or p.ticker,
                "asset_class": p.asset_class,
                "liquidity_fund": p.is_liquidity_fund,
                "quantity": p.quantity,
                "avg_price": p.avg_price,
                "last_price": last,
                "market_value": market_value,
                "cost_basis": cost,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "source": p.source,
            }
        )
    return rows
