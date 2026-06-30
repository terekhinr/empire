#!/usr/bin/env python3
"""Экспорт email из data/pension_waitlist.json для рассылки."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAITLIST = ROOT / "data" / "pension_waitlist.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export pension waitlist emails")
    parser.add_argument("--source", help="Filter by source (gift, site_form, …)")
    parser.add_argument("--csv", action="store_true", help="CSV to stdout")
    args = parser.parse_args()

    if not WAITLIST.is_file():
        print("No waitlist file.", file=sys.stderr)
        return 1

    rows = json.loads(WAITLIST.read_text(encoding="utf-8"))
    if args.source:
        rows = [r for r in rows if r.get("source") == args.source]

    if args.csv:
        w = csv.writer(sys.stdout)
        w.writerow(["email", "source", "created_at", "utm_source", "utm_campaign"])
        for r in rows:
            w.writerow([
                r.get("email", ""),
                r.get("source", ""),
                r.get("created_at", ""),
                r.get("utm_source", ""),
                r.get("utm_campaign", ""),
            ])
    else:
        for r in rows:
            print(r.get("email", ""))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
