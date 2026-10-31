#!/usr/bin/env python3
"""Удаляет повторяющиеся отзывы об одной и той же бане.

Как накопились дубли: в парсере Яндекса идентификатор отзыва считался через
встроенный hash() Python. Он меняется при каждом запуске процесса, поэтому
ночная выгрузка снова и снова записывала тот же текст как «новый».

Что делает скрипт:
  1. Внутри одной бани оставляет один отзыв с одинаковым текстом
     (предпочитает уже одобренный, затем более ранний id).
  2. Если один и тот же текст висит на нескольких банях — оставляет его
     на самой «сильной» карточке (опубликованная, с яндекс-ссылкой, больше
     отзывов), с остальных снимает.
  3. Пересчитывает стабильный source_id (sha1 текста).
     reviews_total с Яндекса НЕ перезаписываем локальным COUNT
     (иначе quality gate по посещаемости ломается).

Запуск:
    python tools/banya_review_dedupe.py --show
    python tools/banya_review_dedupe.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "empire.db"

STATUS_RANK = {"approved": 0, "pending": 1, "hidden": 2}


def stable_review_source_id(text: str) -> str:
    """Стабильный id: один и тот же текст → один и тот же ключ между запусками."""
    return hashlib.sha1((text or "").strip().encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _norm(text: str | None) -> str:
    return (text or "").strip()


def pick_keeper(rows: list[sqlite3.Row]) -> sqlite3.Row:
    return min(
        rows,
        key=lambda r: (
            STATUS_RANK.get(r["status"] or "", 9),
            r["id"],
        ),
    )


def _spot_strength(con: sqlite3.Connection, spot_id: int) -> tuple:
    row = con.execute(
        "SELECT status, yandex_url, reviews_total FROM banya_spots WHERE id = ?",
        (spot_id,),
    ).fetchone()
    if not row:
        return (9, 1, 0, spot_id)
    status_rank = {"published": 0, "draft": 1, "hidden": 2}.get(row["status"] or "", 9)
    no_url = 0 if (row["yandex_url"] or "").strip() else 1
    return (status_rank, no_url, -(row["reviews_total"] or 0), spot_id)


def same_spot_dupes(con: sqlite3.Connection) -> list[tuple[list[int], int]]:
    """Группы (лишние id, id который оставляем) по spot_id+текст."""
    grouped: dict[tuple[int, str], list[sqlite3.Row]] = defaultdict(list)
    for r in con.execute(
        "SELECT id, spot_id, text, status FROM banya_reviews "
        "WHERE text IS NOT NULL AND TRIM(text) != ''"
    ):
        grouped[(r["spot_id"], _norm(r["text"]))].append(r)
    out: list[tuple[list[int], int]] = []
    for rows in grouped.values():
        if len(rows) < 2:
            continue
        keep = pick_keeper(rows)
        extra = [r["id"] for r in rows if r["id"] != keep["id"]]
        out.append((extra, keep["id"]))
    return out


def cross_spot_dupes(con: sqlite3.Connection) -> list[tuple[list[int], int]]:
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in con.execute(
        "SELECT id, spot_id, text, status FROM banya_reviews "
        "WHERE text IS NOT NULL AND LENGTH(TRIM(text)) >= 40"
    ):
        grouped[_norm(r["text"]).lower()].append(r)
    out: list[tuple[list[int], int]] = []
    for rows in grouped.values():
        spots = {r["spot_id"] for r in rows}
        if len(spots) < 2:
            continue
        winner_spot = min(spots, key=lambda sid: _spot_strength(con, sid))
        keep_candidates = [r for r in rows if r["spot_id"] == winner_spot]
        keep = pick_keeper(keep_candidates)
        extra = [r["id"] for r in rows if r["id"] != keep["id"]]
        if extra:
            out.append((extra, keep["id"]))
    return out


def _delete_ids(con: sqlite3.Connection, ids: list[int]) -> int:
    if not ids:
        return 0
    n = 0
    for i in range(0, len(ids), 400):
        chunk = ids[i : i + 400]
        ph = ",".join("?" * len(chunk))
        cur = con.execute(f"DELETE FROM banya_reviews WHERE id IN ({ph})", chunk)
        n += cur.rowcount or 0
    return n


def refresh_review_counts(con: sqlite3.Connection, now: str) -> None:
    """Только updated_at. reviews_total = счётчик Яндекса (enrich/refresh), не COUNT."""
    con.execute("UPDATE banya_spots SET updated_at = ?", (now,))


def recompute_source_ids(con: sqlite3.Connection) -> int:
    n = 0
    rows = list(con.execute("SELECT id, text FROM banya_reviews"))
    for r in rows:
        sid = stable_review_source_id(r["text"] or "")
        con.execute("UPDATE banya_reviews SET source_id = ? WHERE id = ?", (sid, r["id"]))
        n += 1
    return n


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--show", action="store_true", help="только показать, не писать")
    p.add_argument("--apply", action="store_true", help="удалить дубли в БД")
    args = p.parse_args(argv)
    if not args.show and not args.apply:
        args.show = True

    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=60000")

    before = con.execute("SELECT COUNT(*) FROM banya_reviews").fetchone()[0]
    same = same_spot_dupes(con)
    extra_same = sum(len(x[0]) for x in same)
    print(f"Отзывов сейчас: {before}")
    print(f"Повторы внутри одной бани: {len(same)} групп, лишних строк: {extra_same}")

    if args.apply:
        deleted_same = _delete_ids(con, [i for extra, _ in same for i in extra])
        print(f"  удалено внутри бани: {deleted_same}")
    else:
        print("  (show: не удаляем)")
        for extra, keep in sorted(same, key=lambda t: -len(t[0]))[:8]:
            print(f"    keep #{keep}, drop {len(extra)} ids")

    cross = cross_spot_dupes(con)
    extra_cross = sum(len(x[0]) for x in cross)
    print(f"Одинаковый текст на разных банях: {len(cross)} групп, лишних строк: {extra_cross}")

    if args.apply:
        deleted_cross = _delete_ids(con, [i for extra, _ in cross for i in extra])
        print(f"  удалено между банями: {deleted_cross}")
        n_src = recompute_source_ids(con)
        print(f"  пересчитан source_id: {n_src}")
        now = _now()
        refresh_review_counts(con, now)
        after = con.execute("SELECT COUNT(*) FROM banya_reviews").fetchone()[0]
        approved = con.execute(
            "SELECT COUNT(*) FROM banya_reviews WHERE status='approved'"
        ).fetchone()[0]
        con.commit()
        print(f"\nГотово: было {before}, стало {after} (одобренных {approved})")
        print(f"Удалено всего: {before - after}")
    else:
        print("\n--- show-only, изменений в БД нет. Запусти с --apply ---")

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
