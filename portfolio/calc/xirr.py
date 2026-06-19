"""XIRR по денежным потокам (пополнения / выводы + текущая стоимость)."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

from pyxirr import xirr as _pyxirr


def build_cashflow_series(
    conn: sqlite3.Connection,
    current_portfolio_value: float,
    as_of: date | None = None,
) -> tuple[list[float], list[date]]:
    """
    В XIRR входят только движения денег между инвестором и брокером:
    deposit (отриц.), withdrawal/dividend_paid_out (полож.), плюс текущая стоимость.
    """
    as_of = as_of or date.today()
    amounts: list[float] = []
    dates: list[date] = []

    rows = conn.execute(
        """
        SELECT flow_date, amount, flow_type FROM cashflows ORDER BY flow_date
        """
    ).fetchall()
    for r in rows:
        d = date.fromisoformat(str(r["flow_date"])[:10])
        amt = float(r["amount"])
        ft = r["flow_type"]
        if ft == "deposit":
            amounts.append(-abs(amt))
        elif ft in ("withdrawal", "dividend_withdrawn"):
            amounts.append(abs(amt))
        else:
            amounts.append(amt)
        dates.append(d)

    if current_portfolio_value > 0:
        amounts.append(current_portfolio_value)
        dates.append(as_of)

    return amounts, dates


def compute_xirr(
    conn: sqlite3.Connection,
    current_portfolio_value: float,
    as_of: date | None = None,
) -> float | None:
    amounts, dates = build_cashflow_series(conn, current_portfolio_value, as_of)
    if len(amounts) < 2:
        return None
    try:
        return float(_pyxirr(dates, amounts))
    except Exception:
        return None


def cashflow_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT flow_type, SUM(amount) AS total FROM cashflows GROUP BY flow_type
        """
    ).fetchall()
    return {r["flow_type"]: float(r["total"]) for r in rows}
