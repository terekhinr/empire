"""Импорт брокерского отчёта Газпромбанк / Ньютон (HTML, Excel export)."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from portfolio.asset_classify import classify_asset
from portfolio.db import broker_account_id, upsert_instrument, upsert_manual_position


def _num(s: str) -> float:
    s = s.replace("\xa0", " ").replace(" ", "").replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    return float(s) if s else 0.0


def import_gpb_html(conn: sqlite3.Connection, path: str | Path) -> dict[str, Any]:
    path = Path(path)
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    account_id = broker_account_id(conn, "gpb")
    conn.execute(
        "DELETE FROM manual_positions WHERE account_id=? AND note LIKE 'gpb_html:%'",
        (account_id,),
    )
    report_date = _report_end_date(path.name)
    updated = 0
    in_portfolio = False

    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if not cells:
            continue
        row_text = " ".join(cells)
        if "Состояние портфеля ценных бумаг" in row_text:
            in_portfolio = False
        if "Наименование ЦБ" in row_text and "ISIN" in row_text:
            in_portfolio = True
            continue
        if not in_portfolio:
            continue
        if len(cells) < 13:
            continue
        isin = cells[3] if len(cells) > 3 else ""
        if not re.match(r"^RU[A-Z0-9]{9,12}$", isin):
            continue
        name = cells[1] if len(cells) > 1 else isin
        try:
            qty = _num(cells[7])
            close_price = _num(cells[11])
        except (IndexError, ValueError):
            continue
        if qty <= 0:
            continue
        asset_class, is_liq = classify_asset(isin, name=name)
        iid = upsert_instrument(
            conn,
            isin,
            isin=isin,
            name=name[:200],
            asset_class=asset_class,
            is_liquidity_fund=is_liq,
        )
        upsert_manual_position(
            conn,
            account_id=account_id,
            instrument_id=iid,
            quantity=qty,
            avg_price=close_price if close_price > 0 else None,
            note=f"gpb_html:{path.name}",
        )
        if close_price > 0:
            from datetime import date

            today = date.today().isoformat()
            for px_date in (report_date, today):
                conn.execute(
                    """
                    INSERT INTO price_cache (ticker, price_date, price, source)
                    VALUES (?, ?, ?, 'gpb_report')
                    ON CONFLICT(ticker, price_date) DO UPDATE SET price=excluded.price, source=excluded.source
                    """,
                    (isin, px_date, close_price),
                )
        updated += 1

    return {"broker": "gpb", "positions_updated": updated, "file": path.name, "report_date": report_date}


def _report_end_date(filename: str) -> str:
    from datetime import date

    m = re.search(r"_(\d{8})_(\d{8})_", filename)
    if m:
        s = m.group(2)
        try:
            return date(int(s[0:4]), int(s[4:6]), int(s[6:8])).isoformat()
        except ValueError:
            pass
    return date.today().isoformat()
