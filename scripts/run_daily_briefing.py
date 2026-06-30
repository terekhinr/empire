#!/usr/bin/env python3
"""Утренний брифинг Empire (L1+L2). Cron: 0 8 * * * MSK."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from planning_insights import run_daily_briefing  # noqa: E402


def main() -> int:
    result = run_daily_briefing(use_llm=True, notify_telegram=True)
    print(json.dumps(
        {
            "day": result.get("day"),
            "checklist_id": result.get("checklist_id"),
            "focus_items": result.get("focus_items"),
            "telegram_sent": result.get("telegram_sent"),
            "file_path": result.get("file_path"),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
