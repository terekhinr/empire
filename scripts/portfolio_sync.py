#!/usr/bin/env python3
"""Cron: котировки MOEX + Т-Банк API + месячный снимок."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from portfolio.sync import run_full_sync  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("portfolio_sync")


def main() -> int:
    res = run_full_sync()
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if res.get("tbank", {}).get("error"):
        log.warning("tbank: %s", res["tbank"]["error"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
