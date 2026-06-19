#!/usr/bin/env python3
"""Скрывает шумные драфты в banya_spots.

Шум = status='draft' AND (yandex_url пуст) AND rating_avg IS NULL
       AND title попадает под "generic" regex ИЛИ length(trim(title)) <= 4.

Запуск:
  python3 tools/banya_hide_noise.py                # dry-run (показать список)
  python3 tools/banya_hide_noise.py --apply        # выставить status='hidden'
  python3 tools/banya_hide_noise.py --region MO    # только регион
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "empire.db"

GENERIC = re.compile(
    r"^(баня|сауна|бани|саун[аы]|sauna|bath|public bath|"
    r"общественная баня|термы?|hammam|хамам|баня[-\s]*сауна|"
    r"сауна[-\s]*баня)\s*$",
    re.IGNORECASE,
)


def is_noise_title(title: str | None) -> bool:
    t = (title or "").strip().strip("\"'«»“”")
    if not t:
        return True
    if len(t) <= 4:
        return True
    if GENERIC.match(t):
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="реально проставить status='hidden'")
    ap.add_argument("--region", default=None, help="ограничить регионом (MO/SPB/MSK)")
    args = ap.parse_args()

    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    where = [
        "status = 'draft'",
        "(yandex_url IS NULL OR TRIM(yandex_url) = '')",
        "rating_avg IS NULL",
    ]
    params: list = []
    if args.region:
        where.append("region = ?")
        params.append(args.region.upper())

    sql = f"SELECT id, title, city, region FROM banya_spots WHERE {' AND '.join(where)} ORDER BY region, id"
    rows = cur.execute(sql, params).fetchall()

    noise = [r for r in rows if is_noise_title(r["title"])]
    print(f"candidates (draft + no yurl + no rating): {len(rows)}")
    print(f"noise (generic title): {len(noise)}")
    by_region: dict[str, int] = {}
    for r in noise:
        by_region[r["region"] or "?"] = by_region.get(r["region"] or "?", 0) + 1
    for reg, n in sorted(by_region.items()):
        print(f"  {reg}: {n}")

    print()
    print("preview:")
    for r in noise[:30]:
        print(f"  #{r['id']:>4} [{r['region'] or '-'}] {r['city'] or '-':<24} {r['title']!r}")
    if len(noise) > 30:
        print(f"  …+{len(noise) - 30} more")

    if not args.apply:
        print()
        print("dry-run. Запусти с --apply, чтобы скрыть.")
        return 0

    ids = [r["id"] for r in noise]
    if not ids:
        print("nothing to hide.")
        return 0

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    placeholders = ",".join("?" * len(ids))
    cur.execute(
        f"UPDATE banya_spots SET status='hidden', updated_at=? WHERE id IN ({placeholders})",
        [now, *ids],
    )
    con.commit()
    print(f"hidden: {cur.rowcount}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
