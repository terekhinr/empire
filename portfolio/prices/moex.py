"""Котировки MOEX ISS: акции, фонды, облигации (грязные цены), металлы."""

from __future__ import annotations

import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Iterable

import requests

from portfolio.importers.isin_ticker import isin_to_ticker, looks_like_isin, query_to_ticker
from portfolio.asset_classify import CASH_TICKERS

log = logging.getLogger(__name__)

ISS_BASE = "https://iss.moex.com/iss"

# engine, market, board, is_bond (LAST в % от номинала)
_BOARD_SPECS: tuple[tuple[str, str, str, bool], ...] = (
    ("currency", "selt", "CETS", False),
    ("stock", "shares", "TQBR", False),
    ("stock", "shares", "TQTF", False),
    ("stock", "shares", "SMAL", False),
    ("stock", "bonds", "TQOB", True),
    ("stock", "bonds", "TQCB", True),
)


def bond_dirty_price(last_pct: float, facevalue: float, accrued: float = 0.0) -> float:
    """Грязная цена облигации в ₽: номинал × LAST%/100 + НКД."""
    return float(facevalue) * float(last_pct) / 100.0 + float(accrued or 0.0)


def _iss_table(block: dict) -> list[dict]:
    cols = block.get("columns") or []
    rows = block.get("data") or []
    return [dict(zip(cols, row)) for row in rows]


def _first_number(*vals) -> float | None:
    for val in vals:
        if val is None or val == "":
            continue
        try:
            n = float(val)
        except (TypeError, ValueError):
            continue
        if n > 0:
            return n
    return None


def _fetch_board(engine: str, market: str, board: str, is_bond: bool) -> dict[str, float]:
    url = f"{ISS_BASE}/engines/{engine}/markets/{market}/boards/{board}/securities.json"
    params = {
        "iss.meta": "off",
        "iss.only": "securities,marketdata",
        "securities.columns": "SECID,ISIN,FACEVALUE,SHORTNAME,ACCRUEDINT,PREVPRICE",
        "marketdata.columns": "SECID,LAST,MARKETPRICE,LCURRENTPRICE,CLOSEPRICE,CURRENTVALUE",
    }
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    secs = {str(row.get("SECID") or "").upper(): row for row in _iss_table(data.get("securities") or {})}
    out: dict[str, float] = {}
    for md in _iss_table(data.get("marketdata") or {}):
        secid = str(md.get("SECID") or "").upper()
        if not secid:
            continue
        last = _first_number(
            md.get("LAST"),
            md.get("LCURRENTPRICE"),
            md.get("MARKETPRICE"),
            md.get("CLOSEPRICE"),
            md.get("CURRENTVALUE"),
        )
        sec = secs.get(secid, {})
        if last is None:
            last = _first_number(sec.get("PREVPRICE"))
        if last is None:
            continue
        if is_bond:
            face = _first_number(sec.get("FACEVALUE")) or 1000.0
            accrued = 0.0
            try:
                accrued = float(sec.get("ACCRUEDINT") or 0)
            except (TypeError, ValueError):
                accrued = 0.0
            last = bond_dirty_price(last, face, accrued)
        out[secid] = last
        isin = str(sec.get("ISIN") or "").upper()
        if isin and isin != secid:
            out.setdefault(isin, last)
    return out


def _fetch_security_fallback(ticker: str) -> float | None:
    """Одна бумага через ISS, если её не было на стандартных досках."""
    ticker = ticker.strip().upper()
    try:
        r = requests.get(
            f"{ISS_BASE}/securities/{ticker}.json",
            params={"iss.meta": "off", "iss.only": "boards"},
            timeout=12,
        )
        r.raise_for_status()
        boards = _iss_table(r.json().get("boards") or {})
    except Exception as exc:
        log.debug("iss boards %s: %s", ticker, exc)
        return None

    preferred = sorted(
        boards,
        key=lambda b: (
            0 if b.get("is_primary") in (1, "1", True) else 1,
            0 if b.get("primary_board") in (1, "1", True) else 1,
        ),
    )
    for b in preferred:
        engine = str(b.get("engine") or "")
        market = str(b.get("market") or "")
        board = str(b.get("boardid") or b.get("primary_boardid") or "")
        if not (engine and market and board):
            continue
        is_bond = "bond" in market.lower()
        try:
            url = (
                f"{ISS_BASE}/engines/{engine}/markets/{market}/boards/{board}"
                f"/securities/{ticker}.json"
            )
            r = requests.get(url, params={"iss.meta": "off"}, timeout=12)
            r.raise_for_status()
            data = r.json()
        except Exception:
            continue
        secs = _iss_table(data.get("securities") or {})
        mds = _iss_table(data.get("marketdata") or {})
        md = mds[0] if mds else {}
        sec = secs[0] if secs else {}
        last = _first_number(
            md.get("LAST"),
            md.get("LCURRENTPRICE"),
            md.get("MARKETPRICE"),
            md.get("CLOSEPRICE"),
            md.get("CURRENTVALUE"),
            sec.get("PREVPRICE"),
            sec.get("PREVLEGALCLOSEPRICE"),
        )
        if last is None:
            continue
        if is_bond:
            face = _first_number(sec.get("FACEVALUE")) or 1000.0
            try:
                accrued = float(sec.get("ACCRUEDINT") or 0)
            except (TypeError, ValueError):
                accrued = 0.0
            last = bond_dirty_price(last, face, accrued)
        return last
    return None


def fetch_prices(tickers: Iterable[str]) -> dict[str, float]:
    wanted_raw = sorted({x.strip().upper() for x in tickers if x})
    if not wanted_raw:
        return {}

    aliases: dict[str, str] = {}
    wanted: set[str] = set()
    for t in wanted_raw:
        canon = t.rstrip("@")
        wanted.add(canon)
        if canon != t:
            aliases[t] = canon
        if t.startswith("RU") and len(t) >= 11:
            mapped = isin_to_ticker(t)
            if mapped:
                aliases[t] = mapped
                wanted.add(mapped)

    board_quotes: dict[str, float] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {
            pool.submit(_fetch_board, engine, market, board, is_bond): board
            for engine, market, board, is_bond in _BOARD_SPECS
        }
        for fut in as_completed(futs):
            board = futs[fut]
            try:
                board_quotes.update(fut.result())
            except Exception as exc:
                log.warning("moex board %s: %s", board, exc)

    out: dict[str, float] = {}
    missing: list[str] = []
    for t in wanted:
        if t in board_quotes:
            out[t] = board_quotes[t]
        else:
            missing.append(t)

    for t in missing:
        px = _fetch_security_fallback(t)
        if px is not None:
            out[t] = px

    unresolved = [t for t in wanted_raw if t not in out and aliases.get(t) not in out]
    for t in unresolved:
        if len(t.rstrip("@")) < 4 and not looks_like_isin(t):
            continue
        mapped = query_to_ticker(t)
        if not mapped:
            continue
        aliases[t] = mapped
        if mapped in out:
            continue
        if mapped in board_quotes:
            out[mapped] = board_quotes[mapped]
            continue
        px = _fetch_security_fallback(mapped)
        if px is not None:
            out[mapped] = px

    for original, mapped in aliases.items():
        if original not in out and mapped in out:
            out[original] = out[mapped]
    for t in wanted_raw:
        if t not in out and (t in CASH_TICKERS or t.rstrip("@") in CASH_TICKERS):
            out[t] = 1.0
    return {k: v for k, v in out.items() if k in set(wanted_raw) | set(aliases.values())}


def fetch_price(ticker: str) -> float | None:
    got = fetch_prices([ticker])
    t = ticker.strip().upper()
    if t in got:
        return got[t]
    mapped = isin_to_ticker(t)
    if mapped and mapped in got:
        return got[mapped]
    return None


def cache_prices(
    conn: sqlite3.Connection,
    prices: dict[str, float],
    price_date: str | None = None,
    *,
    source: str = "moex",
) -> int:
    d = price_date or date.today().isoformat()
    n = 0
    for ticker, price in prices.items():
        conn.execute(
            """
            INSERT INTO price_cache (ticker, price_date, price, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker, price_date) DO UPDATE SET
                price=excluded.price,
                source=excluded.source
            """,
            (ticker.strip().upper(), d, float(price), source),
        )
        n += 1
    return n


def get_cached_or_fetch(
    conn: sqlite3.Connection,
    tickers: Iterable[str],
    *,
    force: bool = False,
    network: bool = True,
) -> dict[str, float]:
    """
    Актуальные цены на дату анализа (сегодня).
    force=True — всегда ходит на MOEX.
    network=False — только SQLite, без ISS (страницы кабинета).
    Иначе берёт сегодняшнюю MOEX-котировку; недостающие догружает.
    Отчёт брокера — только запасной вариант, если биржа не ответила.
    """
    today = date.today().isoformat()
    tickers = sorted({t.strip().upper() for t in tickers if t})
    out: dict[str, float] = {}
    missing: list[str] = []

    for t in tickers:
        if force and network:
            missing.append(t)
            continue
        row = conn.execute(
            """
            SELECT price FROM price_cache
            WHERE ticker=? AND price_date=? AND source='moex'
            """,
            (t, today),
        ).fetchone()
        if row:
            out[t] = float(row["price"])
        else:
            missing.append(t)

    if not missing:
        return out

    if not network:
        for t in missing:
            if t in CASH_TICKERS or t.rstrip("@") in CASH_TICKERS:
                out[t] = 1.0
                continue
            row = conn.execute(
                """
                SELECT price FROM price_cache
                WHERE ticker=? ORDER BY price_date DESC LIMIT 1
                """,
                (t,),
            ).fetchone()
            if row:
                out[t] = float(row["price"])
        return out

    try:
        fresh = fetch_prices(missing)
    except Exception as exc:
        log.warning("moex fetch: %s", exc)
        fresh = {}
    if fresh:
        cache_prices(conn, fresh, today, source="moex")
        for t, px in fresh.items():
            if t in tickers or t in missing:
                out[t] = px
    still = [t for t in missing if t not in out]
    for t in still:
        if t in CASH_TICKERS or t.rstrip("@") in CASH_TICKERS:
            out[t] = 1.0
            continue
        mapped = None
        long_enough = len(t.rstrip("@")) >= 4 or looks_like_isin(t)
        if long_enough and (
            (t.startswith("RU") and len(t) >= 11)
            or t.endswith("@")
            or any("А" <= ch <= "Я" for ch in t)
        ):
            mapped = query_to_ticker(t)
        if not mapped:
            row = conn.execute(
                "SELECT name FROM instruments WHERE upper(ticker)=?", (t,)
            ).fetchone()
            if row and row["name"]:
                mapped = query_to_ticker(str(row["name"]))
        if mapped and mapped not in out and mapped not in fresh:
            extra = fetch_prices([mapped])
            fresh.update(extra)
            if extra:
                cache_prices(conn, extra, today, source="moex")
        if mapped and mapped in out:
            out[t] = out[mapped]
            continue
        if mapped and mapped in fresh:
            out[t] = fresh[mapped]
            continue
        row = conn.execute(
            """
            SELECT price FROM price_cache
            WHERE ticker=? ORDER BY price_date DESC LIMIT 1
            """,
            (t,),
        ).fetchone()
        if row:
            out[t] = float(row["price"])
            continue
        if mapped:
            row = conn.execute(
                """
                SELECT price FROM price_cache
                WHERE ticker=? ORDER BY price_date DESC LIMIT 1
                """,
                (mapped,),
            ).fetchone()
            if row:
                out[t] = float(row["price"])
    return out

def quote_dates(conn: sqlite3.Connection, tickers: Iterable[str]) -> dict[str, str]:
    today = date.today().isoformat()
    out: dict[str, str] = {}
    for t in {x.strip().upper() for x in tickers if x}:
        row = conn.execute(
            """
            SELECT price_date FROM price_cache
            WHERE ticker=? ORDER BY
                CASE WHEN price_date=? THEN 0 ELSE 1 END,
                price_date DESC
            LIMIT 1
            """,
            (t, today),
        ).fetchone()
        if row:
            out[t] = str(row["price_date"])
    return out
