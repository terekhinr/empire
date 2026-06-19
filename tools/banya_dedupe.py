#!/usr/bin/env python3
"""Детектор и распуталка ложных дублей в `banya_spots`.

Сценарий проблемы:
  парсер enrich искал каждую OSM-точку «Баня»/«Сауна» через text-search
  на yandex.ru/maps, и для безымянных точек Яндекс отвечал одной крупной
  карточкой («Сауны на Коллонтай»). В итоге один Я-URL подцепил 27
  разных OSM-точек, у всех тот же `phone` и `rating_avg`.

Что делает скрипт:
  1. Группирует записи по непустому `yandex_url`.
  2. В группах с >1 записями выбирает «канонический» (самый информативный title).
  3. У остальных очищает `yandex_url`, `phone`, `rating_avg`, `site_url`.
     Сами объекты не трогает (OSM-точки могут быть реальными филиалами).

Запуск:
    python tools/banya_dedupe.py --show          # показать группы
    python tools/banya_dedupe.py --apply         # выполнить очистку
    python tools/banya_dedupe.py --apply --min 2 # только группы с >= 2
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "empire.db"

# Любой title из этого набора считается «безымянным» (низкий приоритет
# на выбор канонической записи).
GENERIC_TITLES = {
    "баня", "бани", "сауна", "сауны", "банный комплекс",
    "общественная баня", "русская баня", "финская баня",
}


def _normalize_title(t: str | None) -> str:
    return (t or "").strip().lower()


def _score(title: str | None) -> int:
    """Чем больше — тем выше приоритет быть канонической записью."""
    nt = _normalize_title(title)
    if not nt:
        return 0
    if nt in GENERIC_TITLES:
        return 1
    # Длина + бонус за неприсутствие в GENERIC даёт длинному «Правобережные
    # Бани» более высокий счёт, чем «Сауны Питера», и тем более «Баня».
    return 10 + min(len(nt), 40)


def fetch_groups(con: sqlite3.Connection, min_cnt: int = 2) -> list[list[dict]]:
    rows = con.execute(
        "SELECT id, slug, title, yandex_url, phone, rating_avg, site_url, status "
        "FROM banya_spots "
        "WHERE yandex_url IS NOT NULL AND TRIM(yandex_url) != '' "
        "  AND status != 'hidden' "
        "ORDER BY yandex_url, id"
    ).fetchall()
    by_url: dict[str, list[dict]] = {}
    for r in rows:
        d = dict(zip(
            ["id", "slug", "title", "yandex_url", "phone", "rating_avg",
             "site_url", "status"], r,
        ))
        by_url.setdefault(d["yandex_url"], []).append(d)
    return [g for g in by_url.values() if len(g) >= min_cnt]


def pick_canonical(group: list[dict]) -> dict:
    return max(group, key=lambda d: (_score(d["title"]), -d["id"]))


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--show", action="store_true", help="только показать группы")
    p.add_argument("--apply", action="store_true",
                   help="очистить yandex_url/phone/rating_avg/site_url у не-канон записей")
    p.add_argument("--min", type=int, default=2, help="мин. размер группы")
    args = p.parse_args(argv)

    if not args.show and not args.apply:
        args.show = True

    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")

    groups = fetch_groups(con, args.min)
    total_dupes = sum(len(g) - 1 for g in groups)
    print(f"Найдено групп: {len(groups)} (с дублями ≥ {args.min}), записей-дубликатов: {total_dupes}")
    if not groups:
        return 0

    cleared = 0
    for g in sorted(groups, key=lambda gg: -len(gg)):
        canon = pick_canonical(g)
        url_short = canon["yandex_url"][:70]
        print(f"\n— url={url_short} (×{len(g)})")
        print(f"   ✓ keep  #{canon['id']:4d}  {canon['title']}")
        for d in g:
            if d["id"] == canon["id"]:
                continue
            print(f"   ✗ clear #{d['id']:4d}  {d['title']}")
            if args.apply:
                con.execute(
                    "UPDATE banya_spots SET "
                    "  yandex_url = NULL, phone = NULL, rating_avg = NULL, site_url = NULL, "
                    "  updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ?",
                    (d["id"],),
                )
                cleared += 1
    if args.apply:
        con.commit()
        print(f"\n--- applied: очищено {cleared} записей ---")
    else:
        print("\n--- show-only, изменений в БД нет. Запусти с --apply ---")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
