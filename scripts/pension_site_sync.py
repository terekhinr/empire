#!/usr/bin/env python3
"""Синхронизация ленты «На пенсию НИКОГДА» на сайте без ручного участия.

Что делает:
  1. В БД помечает republish-дубликаты (тот же заголовок) как rejected —
     на сайте и в RSS остаётся одна версия.
  2. Пересобирает media/rss_pension.xml для Дзена.
  3. Печатает сводку (сколько уникальных статей на /articles).

Запуск:
  ./venv/bin/python scripts/pension_site_sync.py
  ./venv/bin/python scripts/pension_site_sync.py --dry
Таймер: deploy/empire-pension-site-sync.{service,timer}
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")

from pension_site_feed import pension_title_key  # noqa: E402

DB = ROOT / "empire.db"


def _sync_dedupe_db(*, dry: bool) -> tuple[int, int]:
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    rows = list(
        con.execute(
            "SELECT id, text_content, created_at FROM post_drafts "
            "WHERE persona_key='pension' AND status='published' "
            "ORDER BY id ASC"
        )
    )
    keep: dict[str, int] = {}
    drop: list[int] = []
    for r in rows:
        key = pension_title_key(r["text_content"])
        if not key:
            key = f"id:{r['id']}"
        if key in keep:
            drop.append(r["id"])
        else:
            keep[key] = r["id"]
    if dry:
        print(f"dry: unique={len(keep)} would_reject={len(drop)} ids={drop}")
        con.close()
        return len(keep), len(drop)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for i in drop:
        con.execute(
            "UPDATE post_drafts SET status='rejected', decision='site_dedupe', "
            "decided_at=? WHERE id=? AND status='published'",
            (now, i),
        )
    con.commit()
    left = con.execute(
        "SELECT COUNT(*) FROM post_drafts WHERE persona_key='pension' AND status='published'"
    ).fetchone()[0]
    con.close()
    print(f"dedupe: kept={len(keep)} rejected={len(drop)} published_now={left}")
    return left, len(drop)


async def _regen_rss() -> bool:
    from rss_maker import generate_pension_zen_rss

    ok = await generate_pension_zen_rss()
    print(f"rss: {'ok' if ok else 'FAIL'} → media/rss_pension.xml")
    return bool(ok)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--skip-rss", action="store_true")
    args = ap.parse_args()
    _sync_dedupe_db(dry=args.dry)
    if args.dry or args.skip_rss:
        return 0
    return 0 if asyncio.run(_regen_rss()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
