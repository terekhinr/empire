#!/usr/bin/env python3
"""Массовое одобрение отзывов: pending → approved.

Собранные с Яндекса отзывы попадают в БД со status=pending; на сайте показываются
только approved. Этот скрипт — «автомодерация» по простым правилам (как dry-run у pubauto).

  python3 tools/banya_review_approve_bulk.py                    # dry-run
  python3 tools/banya_review_approve_bulk.py --apply             # записать
  python3 tools/banya_review_approve_bulk.py --apply --min-rating 4 --limit 50
  python3 tools/banya_review_approve_bulk.py --apply --source yandex --require-rating

Фильтры по умолчанию:
  * status = pending
  * LENGTH(TRIM(text)) >= --min-text (10)
  * рейтинг NULL или >= --min-rating (1); с --require-rating — только не-NULL и >= порога
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "empire.db"


def _refresh_counts(cur: sqlite3.Cursor, spot_ids: set[int], now: str) -> None:
    if not spot_ids:
        return
    for sid in spot_ids:
        cur.execute(
            "UPDATE banya_spots SET reviews_total = ("
            " SELECT COUNT(*) FROM banya_reviews "
            " WHERE spot_id = ? AND status = 'approved'"
            "), updated_at = ? WHERE id = ?",
            (sid, now, sid),
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="реально выставить status=approved")
    ap.add_argument("--min-rating", type=int, default=1, help="минимальная оценка 1..5 (по умолчанию 1)")
    ap.add_argument("--min-text", type=int, default=10, help="минимальная длина текста после trim")
    ap.add_argument("--limit", type=int, default=0, help="максимум строк (0 = без лимита)")
    ap.add_argument("--source", default=None, help="только этот source, напр. yandex")
    ap.add_argument(
        "--require-rating",
        action="store_true",
        help="не одобрять отзывы без числового рейтинга",
    )
    args = ap.parse_args()

    if args.min_rating < 1 or args.min_rating > 5:
        print("--min-rating должен быть 1..5", file=sys.stderr)
        return 2

    con = sqlite3.connect(str(DB), timeout=120.0)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=600000")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    where = [
        "status = 'pending'",
        "LENGTH(TRIM(COALESCE(text,''))) >= ?",
    ]
    qparams: list = [args.min_text]
    if args.source:
        where.append("source = ?")
        qparams.append(args.source.strip())
    if args.require_rating:
        where.append("rating IS NOT NULL AND rating >= ?")
        qparams.append(args.min_rating)
    else:
        where.append("(rating IS NULL OR rating >= ?)")
        qparams.append(args.min_rating)

    sql = (
        "SELECT id, spot_id, source, rating, text FROM banya_reviews WHERE "
        + " AND ".join(where)
        + " ORDER BY id ASC"
    )
    if args.limit and args.limit > 0:
        sql += f" LIMIT {int(args.limit)}"

    rows = cur.execute(sql, qparams).fetchall()
    print(f"candidates: {len(rows)} (min_text={args.min_text}, min_rating={args.min_rating}, "
          f"require_rating={args.require_rating}, source={args.source or 'any'})")
    for r in rows[:25]:
        t = (r["text"] or "")[:60].replace("\n", " ")
        print(f"  #{r['id']:>5} spot={r['spot_id']} src={r['source'] or '-'} "
              f"★{r['rating'] if r['rating'] is not None else '-'}  {t}")
    if len(rows) > 25:
        print(f"  … всего {len(rows)}")

    if not args.apply:
        print("\ndry-run. Запусти с --apply.")
        return 0

    if not rows:
        print("nothing to approve.")
        return 0

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    spot_ids: set[int] = set()
    for attempt in range(45):
        try:
            for r in rows:
                cur.execute(
                    "UPDATE banya_reviews SET status = 'approved' WHERE id = ? AND status = 'pending'",
                    (r["id"],),
                )
                if cur.rowcount:
                    spot_ids.add(int(r["spot_id"]))
            _refresh_counts(cur, spot_ids, now)
            con.commit()
            break
        except sqlite3.OperationalError as e:
            if "locked" not in str(e).lower() or attempt == 44:
                raise
            time.sleep(2.0)
    else:
        return 1

    print(f"\napproved rows: {len(rows)}, spots updated: {len(spot_ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
