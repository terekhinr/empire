"""Котировки MOEX ISS (акции, облигации, фонды)."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date
from typing import Iterable

import requests

log = logging.getLogger(__name__)

ISS_BASE = "https://iss.moex.com/iss"

# board, market, engine для поиска LAST
_MARKET_TRIES = (
    # Драгоценные металлы TOM (GLDRUB_TOM, SLVRUB_TOM)
    ("currency", "selt", "CETS"),
    ("stock", "shares", "TQBR"),
    ("stock", "shares", "TQTF"),
    ("stock", "bonds", "TQOB"),
    ("stock", "bonds", "TQCB"),
    ("stock", "shares", "SMAL"),
)


def _fetch_last(engine: str, market: str, board: str, ticker: str) -> float | None:
    url = (
        f"{ISS_BASE}/engines/{engine}/markets/{market}/boards/{board}/securities/{ticker}.json"
        "?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST,CURRENTVALUE"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        rows = data.get("marketdata", {}).get("data", [])
        if not rows:
            return None
        # LAST at index 1, CURRENTVALUE at 2 for bonds/funds
        last = rows[0][1]
        current = rows[0][2] if len(rows[0]) > 2 else None
        for val in (last, current):
            if val is not None and val != "":
                return float(val)
    except Exception as exc:
        log.debug("moex %s/%s: %s", board, ticker, exc)
    return None


def fetch_price(ticker: str) -> float | None:
    ticker = ticker.strip().upper()
    for engine, market, board in _MARKET_TRIES:
        price = _fetch_last(engine, market, board, ticker)
        if price is not None and price > 0:
            return price
    return None


def fetch_prices(tickers: Iterable[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for t in sorted({x.strip().upper() for x in tickers if x}):
        p = fetch_price(t)
        if p is not None:
            out[t] = p
    return out


def cache_prices(conn: sqlite3.Connection, prices: dict[str, float], price_date: str | None = None) -> int:
    d = price_date or date.today().isoformat()
    n = 0
    for ticker, price in prices.items():
        conn.execute(
            """
            INSERT INTO price_cache (ticker, price_date, price, source)
            VALUES (?, ?, ?, 'moex')
            ON CONFLICT(ticker, price_date) DO UPDATE SET
                price = CASE
                    WHEN price_cache.source IN ('gpb_report', 'vtb_report') THEN price_cache.price
                    ELSE excluded.price
                END,
                source = CASE
                    WHEN price_cache.source IN ('gpb_report', 'vtb_report') THEN price_cache.source
                    ELSE excluded.source
                END
            """,
            (ticker, d, price),
        )
        n += 1
    return n


def get_cached_or_fetch(conn: sqlite3.Connection, tickers: Iterable[str]) -> dict[str, float]:
    today = date.today().isoformat()
    tickers = sorted({t.strip().upper() for t in tickers if t})
    out: dict[str, float] = {}
    missing: list[str] = []
    for t in tickers:
        row = conn.execute(
            "SELECT price FROM price_cache WHERE ticker=? AND price_date=?",
            (t, today),
        ).fetchone()
        if row:
            out[t] = float(row["price"])
            continue
        row = conn.execute(
            "SELECT price FROM price_cache WHERE ticker=? ORDER BY price_date DESC LIMIT 1",
            (t,),
        ).fetchone()
        if row:
            out[t] = float(row["price"])
            continue
        missing.append(t)
    if missing:
        fresh = fetch_prices(missing)
        if fresh:
            cache_prices(conn, fresh, today)
            out.update(fresh)
    return out
