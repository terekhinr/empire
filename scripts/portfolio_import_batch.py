#!/usr/bin/env python3
"""Пакетный импорт всех отчётов из data/portfolio_imports/."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from portfolio.config import IMPORTS_DIR  # noqa: E402
from portfolio.db import db_session, init_db  # noqa: E402
from portfolio.importers.alfa_xls import import_alfa_report  # noqa: E402
from portfolio.importers.detect import detect_broker  # noqa: E402
from portfolio.importers.gpb_html import import_gpb_html  # noqa: E402
from portfolio.importers.vtb_xlsx import import_vtb_report  # noqa: E402
from portfolio.sync import refresh_prices, run_full_sync  # noqa: E402


def _alfa_agreement(path: Path) -> str | None:
    m = re.search(r"(\d{7})", path.name)
    return m.group(1) if m else None


def _alfa_period_end(path: Path) -> date:
    m = re.search(r"-(\d{2}\.\d{2}\.\d{2})\)", path.name)
    if m:
        d, mo, y = m.group(1).split(".")
        return date(2000 + int(y), int(mo), int(d))
    return date.min


def _vtb_period_end(path: Path) -> date:
    try:
        import pandas as pd

        engine = "openpyxl"
        raw = pd.read_excel(path, sheet_name=0, header=None, nrows=3, engine=engine)
        blob = " ".join(str(x) for x in raw.values.flatten() if str(x) != "nan")
        m = re.search(r"по\s+(\d{2}\.\d{2}\.\d{4})", blob)
        if m:
            d, mo, y = m.group(1).split(".")
            return date(int(y), int(mo), int(d))
    except Exception:
        pass
    return date.min


def _gpb_period_end(path: Path) -> date:
    m = re.search(r"_(\d{8})_(\d{8})_", path.name)
    if m:
        s = m.group(2)
        return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
    return date.min


def _pick_newest_alfa(files: list[Path]) -> list[Path]:
    best: dict[str, tuple[date, Path]] = {}
    for p in files:
        agr = _alfa_agreement(p)
        if not agr:
            continue
        end = _alfa_period_end(p)
        if agr not in best or end >= best[agr][0]:
            best[agr] = (end, p)
    return [p for _, p in best.values()]


def import_file(path: Path) -> dict:
    broker = detect_broker(path)
    if not broker:
        return {"file": path.name, "error": "не распознан брокер"}
    with db_session() as conn:
        init_db(conn)
        if broker == "alfa":
            return {**import_alfa_report(conn, path), "file": path.name}
        if broker == "vtb":
            return {**import_vtb_report(conn, path), "file": path.name}
        if broker == "gpb":
            return {**import_gpb_html(conn, path), "file": path.name}
    return {"file": path.name, "error": f"нет импортера для {broker}"}


def main() -> int:
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        p
        for p in IMPORTS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in (".xls", ".xlsx", ".html", ".htm")
    )

    alfa_files = [p for p in files if detect_broker(p) == "alfa"]
    vtb_files = sorted(
        [p for p in files if detect_broker(p) == "vtb"],
        key=_vtb_period_end,
    )
    gpb_files = [p for p in files if detect_broker(p) == "gpb" and p.suffix.lower() in (".html", ".htm")]

    results: list[dict] = []

    chosen_alfa = _pick_newest_alfa(alfa_files)
    for p in chosen_alfa:
        results.append(import_file(p))
    for p in alfa_files:
        if p not in chosen_alfa:
            results.append({"file": p.name, "skipped": "устаревший отчёт Альфы для этого счёта"})

    for p in vtb_files:
        results.append(import_file(p))

    if gpb_files:
        latest_gpb = max(gpb_files, key=_gpb_period_end)
        results.append(import_file(latest_gpb))
        for p in gpb_files:
            if p != latest_gpb:
                results.append({"file": p.name, "skipped": "устаревший GPB"})

    sync = run_full_sync()
    prices = refresh_prices()
    from portfolio.asset_classify import classify_asset

    with db_session() as conn:
        init_db(conn)
        for r in conn.execute("SELECT id, ticker, name FROM instruments").fetchall():
            cls, is_liq = classify_asset(r["ticker"], name=r["name"])
            conn.execute(
                "UPDATE instruments SET asset_class=?, is_liquidity_fund=? WHERE id=?",
                (cls, int(is_liq), r["id"]),
            )
    print(json.dumps({"imports": results, "sync": sync, "prices": prices}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
