#!/usr/bin/env python3
"""Send Web Push for due task reminders (cron every minute)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from planning_push import process_due_reminder_pushes


def main() -> int:
    result = process_due_reminder_pushes()
    if result.get("sent") or result.get("tasks"):
        print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
