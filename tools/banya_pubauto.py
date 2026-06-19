#!/usr/bin/env python3
"""Массовая публикация банных карточек по фильтру.

Критерии по умолчанию (всё одновременно):
  * status = 'draft'
  * phone задан (не NULL и не пустой)
  * yandex_url задан
  * rating_avg >= MIN_RATING (по умолчанию 4.0)
  * среди дублей по yandex_url — оставляем только один (лучший)

Запуск:
  python3 tools/banya_pubauto.py                       # dry-run, все регионы, rating>=4.0
  python3 tools/banya_pubauto.py --region MO           # только МО
  python3 tools/banya_pubauto.py --min-rating 4.3      # строже
  python3 tools/banya_pubauto.py --limit 50            # не более 50
  python3 tools/banya_pubauto.py --apply               # реально опубликовать
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


def _to_float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None


def _execute_publish_update(
    con: sqlite3.Connection,
    cur: sqlite3.Cursor,
    ids: list[int],
    now: str,
    *,
    attempts: int = 45,
    delay_s: float = 2.0,
) -> None:
    placeholders = ",".join("?" * len(ids))
    sql = (
        f"UPDATE banya_spots SET status='published', updated_at=? WHERE id IN ({placeholders})"
    )
    params = [now, *ids]
    for i in range(attempts):
        try:
            cur.execute(sql, params)
            con.commit()
            return
        except sqlite3.OperationalError as e:
            if "locked" not in str(e).lower() or i == attempts - 1:
                raise
            time.sleep(delay_s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="реально опубликовать (UPDATE status='published')")
    ap.add_argument("--region", default=None, help="MO / SPB / MSK")
    ap.add_argument("--min-rating", type=float, default=4.0, help="минимальный рейтинг (по умолчанию 4.0)")
    ap.add_argument("--min-reviews", type=int, default=0, help="минимум отзывов на Яндексе (по умолчанию 0)")
    ap.add_argument("--limit", type=int, default=0, help="максимум публикаций (0 = без лимита)")
    args = ap.parse_args()

    con = sqlite3.connect(str(DB), timeout=120.0)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=60000")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    where = [
        "status = 'draft'",
        "phone IS NOT NULL AND TRIM(phone) != ''",
        "yandex_url IS NOT NULL AND TRIM(yandex_url) != ''",
        "rating_avg IS NOT NULL AND TRIM(rating_avg) != ''",
    ]
    params: list = []
    if args.region:
        where.append("region = ?")
        params.append(args.region.upper())

    sql = (
        "SELECT id, title, city, region, phone, yandex_url, rating_avg, reviews_total "
        f"FROM banya_spots WHERE {' AND '.join(where)} "
        "ORDER BY CAST(rating_avg AS REAL) DESC, reviews_total DESC, id ASC"
    )
    rows = cur.execute(sql, params).fetchall()

    rated = [
        r for r in rows
        if (_to_float(r["rating_avg"]) or 0) >= args.min_rating
        and (r["reviews_total"] or 0) >= args.min_reviews
    ]

    seen_url: dict[str, sqlite3.Row] = {}
    skipped_dup = 0
    for r in rated:
        u = (r["yandex_url"] or "").strip().lower()
        if not u:
            continue
        prev = seen_url.get(u)
        if prev is None:
            seen_url[u] = r
            continue
        prev_score = ((_to_float(prev["rating_avg"]) or 0), prev["reviews_total"] or 0)
        cur_score = ((_to_float(r["rating_avg"]) or 0), r["reviews_total"] or 0)
        if cur_score > prev_score:
            seen_url[u] = r
        skipped_dup += 1

    picked = list(seen_url.values())
    picked.sort(key=lambda r: ((_to_float(r["rating_avg"]) or 0), r["reviews_total"] or 0, -r["id"]), reverse=True)

    if args.limit and len(picked) > args.limit:
        picked = picked[: args.limit]

    by_region: dict[str, int] = {}
    for r in picked:
        by_region[r["region"] or "?"] = by_region.get(r["region"] or "?", 0) + 1

    print(f"candidates (фильтр phone+yurl): {len(rows)}")
    print(f"  rating>={args.min_rating}, reviews>={args.min_reviews}: {len(rated)}")
    print(f"  отброшено дублей по yandex_url: {skipped_dup}")
    print(f"  итого к публикации: {len(picked)}")
    for reg, n in sorted(by_region.items()):
        print(f"    {reg}: {n}")
    print()
    print("preview:")
    show = picked if len(picked) <= 40 else (picked[:30] + picked[-5:])
    for r in show:
        rv = r["rating_avg"] or "-"
        rc = r["reviews_total"] or 0
        print(
            f"  #{r['id']:>4} [{r['region'] or '-'}] "
            f"★{rv:>4} ({rc:>3}) {r['title'][:40]:<40} · {r['city'] or '-'}"
        )
    if len(picked) > 40:
        print(f"  …(всего {len(picked)})")

    if not args.apply:
        print()
        print("dry-run. Запусти с --apply, чтобы опубликовать.")
        return 0

    if not picked:
        print("nothing to publish.")
        return 0

    ids = [r["id"] for r in picked]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _execute_publish_update(con, cur, ids, now)
    print(f"published: {len(ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
