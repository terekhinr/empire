"""Оркестрация синхронизации портфеля."""

from __future__ import annotations

import logging
import threading
from typing import Any

from portfolio.calc.snapshots import save_monthly_snapshot
from portfolio.config import TBANK_TOKEN
from portfolio.db import db_session, init_db
from portfolio.importers.alfa_xls import import_alfa_report
from portfolio.importers.tbank_api import sync_tbank
from portfolio.importers.gpb_html import import_gpb_html
from portfolio.importers.vtb_xlsx import import_vtb_report
from portfolio.prices.moex import get_cached_or_fetch
from portfolio.calc.positions import compute_positions

log = logging.getLogger(__name__)


def refresh_prices(*, force: bool = True) -> dict[str, Any]:
    """Сеть MOEX — без открытой сессии SQLite, иначе GET вкладок ждёт лок 60с."""
    from portfolio.prices.moex import cache_prices, fetch_prices, get_cached_or_fetch
    from portfolio.web_routes import invalidate_bundle

    with db_session() as conn:
        init_db(conn)
        tickers = [p.ticker for p in compute_positions(conn)]
    prices: dict[str, float] = {}
    if force and tickers:
        try:
            prices = fetch_prices(tickers)
        except Exception:
            log.exception("moex fetch during refresh")
            prices = {}
        if prices:
            with db_session(timeout=15, busy_ms=8000) as conn:
                cache_prices(conn, prices)
    else:
        with db_session() as conn:
            prices = get_cached_or_fetch(conn, tickers, force=False, network=False)
    invalidate_bundle()
    return {"tickers": len(tickers), "priced": len(prices), "forced": force}


def refresh_prices_background(*, force: bool = True) -> None:
    threading.Thread(target=refresh_prices, kwargs={"force": force}, daemon=True).start()


def run_full_sync(tbank_days: int = 365) -> dict[str, Any]:
    results: dict[str, Any] = {}
    with db_session() as conn:
        init_db(conn)
        if TBANK_TOKEN:
            try:
                results["tbank"] = sync_tbank(conn, days_back=tbank_days)
            except Exception as exc:
                results["tbank"] = {"error": str(exc)}
                log.exception("tbank sync")
        else:
            results["tbank"] = {"skipped": "PORTFOLIO_TBANK_TOKEN не задан"}

        positions = compute_positions(conn)
        tickers = [p.ticker for p in positions]
        results["prices"] = {"priced": len(get_cached_or_fetch(conn, tickers, force=True))}
        results["snapshot"] = save_monthly_snapshot(conn)
    return results


def import_broker_file(broker: str, path: str) -> dict[str, Any]:
    with db_session() as conn:
        init_db(conn)
        if broker == "alfa":
            return import_alfa_report(conn, path)
        if broker == "vtb":
            return import_vtb_report(conn, path)
        if broker == "gpb":
            return import_gpb_html(conn, path)
        raise ValueError(f"unknown broker: {broker}")
