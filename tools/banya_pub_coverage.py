#!/usr/bin/env python3
"""Публикация покрытия: именованные черновики с координатами → карта.

Не требует телефона и рейтинга (в отличие от banya_pubauto.py).
Безымянные «Баня»/«Сауна» не трогает, кроме регионов, где иначе карта пустая.

Запуск:
  python tools/banya_pub_coverage.py --regions EUROPE_URAL
  python tools/banya_pub_coverage.py --regions EUROPE_URAL --apply
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.banya_hide_noise import is_noise_title
from tools.banya_regions import REGIONS, expand_region_tokens

DB = ROOT / "empire.db"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--regions", default="EUROPE_URAL")
    args = ap.parse_args()

    codes = expand_region_tokens([r.strip() for r in args.regions.split(",") if r.strip()])
    unknown = [c for c in codes if c not in REGIONS]
    if unknown:
        print(f"Неизвестные регионы: {unknown}", file=sys.stderr)
        return 2

    con = sqlite3.connect(str(DB), timeout=120.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=60000")

    ph = ",".join("?" * len(codes))
    drafts = list(
        con.execute(
            f"SELECT id, title, city, region, lat, lon FROM banya_spots "
            f"WHERE status='draft' AND region IN ({ph}) "
            f"AND lat IS NOT NULL AND TRIM(lat)!='' "
            f"AND lon IS NOT NULL AND TRIM(lon)!=''",
            codes,
        )
    )
    named = [r for r in drafts if not is_noise_title(r["title"])]
    named_ids = {r["id"] for r in named}

    already_pub = {
        r[0]
        for r in con.execute(
            f"SELECT DISTINCT region FROM banya_spots "
            f"WHERE status='published' AND region IN ({ph})",
            codes,
        )
    }
    named_by_reg: dict[str, int] = {}
    for r in named:
        named_by_reg[r["region"]] = named_by_reg.get(r["region"], 0) + 1

    fill: list[sqlite3.Row] = []
    for code in codes:
        will_have = (code in already_pub) or named_by_reg.get(code, 0) > 0
        if will_have:
            continue
        leftovers = [r for r in drafts if r["region"] == code and r["id"] not in named_ids]
        fill.extend(leftovers)

    picked = named + fill
    by_reg: dict[str, int] = {}
    for r in picked:
        by_reg[r["region"] or "?"] = by_reg.get(r["region"] or "?", 0) + 1

    print(f"черновиков с координатами: {len(drafts)}")
    print(f"именованных к публикации: {len(named)}")
    print(f"добивка пустых регионов: {len(fill)}")
    print(f"итого на карту: {len(picked)}")
    for code in codes:
        n = by_reg.get(code, 0)
        if n:
            print(f"  {code:6} {REGIONS[code][1]:40} +{n}")

    if fill:
        print("добивка (иначе регион пустой):")
        for r in fill:
            print(f"  #{r['id']} [{r['region']}] {r['city'] or '-'} {r['title']!r}")

    if not args.apply:
        print("\ndry-run. --apply чтобы открыть на карте.")
        return 0

    if not picked:
        print("нечего публиковать.")
        return 0

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    ids = [r["id"] for r in picked]
    for i in range(0, len(ids), 400):
        chunk = ids[i : i + 400]
        qph = ",".join("?" * len(chunk))
        con.execute(
            f"UPDATE banya_spots SET status='published', updated_at=? WHERE id IN ({qph})",
            [now, *chunk],
        )
    con.commit()
    pub = con.execute(
        f"SELECT COUNT(*) FROM banya_spots WHERE status='published' AND region IN ({ph})",
        codes,
    ).fetchone()[0]
    print(f"\nготово: опубликовано {len(ids)}, на карте в этой зоне теперь {pub}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
