#!/usr/bin/env python3
"""Переклассификация всех инструментов в portfolio.db."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from portfolio.asset_classify import classify_asset  # noqa: E402
from portfolio.db import db_session, init_db  # noqa: E402


def main() -> int:
    n = 0
    with db_session() as conn:
        init_db(conn)
        rows = conn.execute("SELECT id, ticker, name, asset_class FROM instruments").fetchall()
        for r in rows:
            cls, is_liq = classify_asset(r["ticker"], name=r["name"])
            conn.execute(
                "UPDATE instruments SET asset_class=?, is_liquidity_fund=? WHERE id=?",
                (cls, int(is_liq), r["id"]),
            )
            n += 1
    print(f"reclassified {n} instruments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
