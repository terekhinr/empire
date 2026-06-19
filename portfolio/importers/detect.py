"""Автоопределение брокера по файлу отчёта."""

from __future__ import annotations

import re
from pathlib import Path


def detect_broker(path: str | Path) -> str | None:
    p = Path(path)
    name = p.name.lower()
    if p.suffix.lower() in (".html", ".htm"):
        text = p.read_text(encoding="utf-8", errors="ignore")[:8000]
        if "ньютон инвестиции" in text.lower() or "brok_rpt_bo" in name:
            return "gpb"
        if "втб" in text.lower():
            return "vtb"
        if "альфа" in text.lower():
            return "alfa"
    if p.suffix.lower() in (".xls", ".xlsx"):
        try:
            import pandas as pd

            engine = "openpyxl" if p.suffix.lower() == ".xlsx" else "xlrd"
            sample = pd.read_excel(p, sheet_name=0, header=None, nrows=12, engine=engine)
            blob = " ".join(str(x) for x in sample.values.flatten() if str(x) != "nan").lower()
            if "втб" in blob or "банка втб" in blob:
                return "vtb"
            if "альфа" in blob or "alfadirect" in blob or "ген. соглашение" in blob:
                return "alfa"
            if "газпром" in blob or "ньютон" in blob:
                return "gpb"
        except Exception:
            pass
    if "брокерский" in name and p.suffix.lower() == ".xls":
        return "alfa"
    if name.startswith("report") and p.suffix.lower() == ".xlsx":
        return "vtb"
    if name.startswith("brok_rpt"):
        return "gpb"
    return None
