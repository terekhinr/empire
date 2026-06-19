"""Месячные снимки стоимости портфеля."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone

from portfolio.calc.positions import compute_positions, enrich_with_prices
from portfolio.prices.moex import get_cached_or_fetch


def _month_key(d: date | None = None) -> str:
    d = d or date.today()
    return d.strftime("%Y-%m")


def save_monthly_snapshot(conn: sqlite3.Connection) -> dict:
    positions = compute_positions(conn)
    tickers = [p.ticker for p in positions]
    prices = get_cached_or_fetch(conn, tickers)
    enriched = enrich_with_prices(positions, prices)
    total = sum(r["market_value"] or 0 for r in enriched)
    by_broker: dict[str, float] = {}
    for r in enriched:
        by_broker[r["broker"]] = by_broker.get(r["broker"], 0) + (r["market_value"] or 0)
    month = _month_key()
    payload = {
        "total": total,
        "by_broker": by_broker,
        "positions_count": len(enriched),
    }
    conn.execute(
        """
        INSERT INTO monthly_snapshots (month, total_value, payload_json, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET
            total_value=excluded.total_value,
            payload_json=excluded.payload_json,
            created_at=excluded.created_at
        """,
        (
            month,
            total,
            json.dumps(payload, ensure_ascii=False),
            datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        ),
    )
    return payload


def load_snapshot_history(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT month, total_value, payload_json FROM monthly_snapshots ORDER BY month"
    ).fetchall()
    out = []
    for r in rows:
        payload = json.loads(r["payload_json"])
        out.append({"month": r["month"], "total_value": float(r["total_value"]), **payload})
    return out
