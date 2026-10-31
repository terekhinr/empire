#!/usr/bin/env python3
"""Скрывает точки, которые не про классическую/общественную баню.

Сигналы (комбинируются):
  1. Название / описание — VIP-сауна, клуб саун, интим, досуг, стрип и т.п.
  2. Агрегаторы-заглушки («Сауны Питера» и аналоги).
  3. Отзывы — эротика / «девушки по часам» / «это не баня».
     Слово «девочки» (= подруги) само по себе НЕ триггер.
     Слово «сауна» в названии само по себе НЕ триггер (в РФ так зовут нормальные объекты).

Статус → hidden (с карты пропадает, из БД не удаляем).
Причина пишется в data/gdepar_hide_offtopic_log.jsonl при --apply.

Запуск:
  ./venv/bin/python tools/banya_hide_offtopic.py --show
  ./venv/bin/python tools/banya_hide_offtopic.py --show --region MSK,MO,SPB,LO
  ./venv/bin/python tools/banya_hide_offtopic.py --apply
  ./venv/bin/python tools/banya_hide_offtopic.py --apply --min-review-score 4
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "empire.db"
LOG_PATH = ROOT / "data" / "gdepar_hide_offtopic_log.jsonl"

# Жёсткие паттерны названия/описания (adult leisure / не баня)
TITLE_HARD = re.compile(
    r"(?:"
    r"интим|эрот(?:ик|ическ)|бордел|проститут|хостес|стриптиз|стрип[-\s]?клуб|"
    r"массажн(?:ый|ая)\s*(?:салон|кабинет)|"
    r"аква[-\s]?досуг|(?<![а-яa-z])досуг(?![а-яa-z])|"
    r"сауна[-\s]?клуб|клуб\s*саун|"
    r"vip[-\s]?саун|"
    r"девушк[аие].{0,24}(?:баня|саун)|(?:баня|саун).{0,24}девушк"
    r")",
    re.IGNORECASE,
)

# Каталоги / сети-агрегаторы без конкретного объекта
TITLE_AGGREGATOR = re.compile(
    r"^(?:"
    r"сауны\s+питера|"
    r"сауны\s+москвы|"
    r"бани\s+питера|"
    r"бани\s+москвы|"
    r"каталог\s+(?:бань|саун)|"
    r"лучшие\s+(?:бани|сауны)\s+(?:москвы|питера|спб)"
    r")\s*$",
    re.IGNORECASE,
)

# Отзывы: сильные маркеры «не наша ниша»
REVIEW_RULES: list[tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"проститут", re.I), 5, "prostitutk"),
    (re.compile(r"\bбляд", re.I), 5, "blyad"),
    (re.compile(r"интим\w*\s*(?:услуг|массаж|встреч|отдых)", re.I), 5, "intim_uslugi"),
    (re.compile(r"\bэрот", re.I), 4, "erotik"),
    (re.compile(r"минет|куннилингус|оральн", re.I), 5, "sex_act"),
    (re.compile(r"секс\w*\s*(?:услуг|работ|услуг)", re.I), 5, "sex_uslugi"),
    (re.compile(r"предоставля\w{0,10}\s*девуш", re.I), 5, "provide_girls"),
    (re.compile(r"девушк\w*\s*(?:по\s*час|в\s*час|заказать|заказать|работают\s+на\s+час)", re.I), 4, "girls_hourly"),
    (re.compile(r"массажистк", re.I), 3, "massazhistka"),
    (re.compile(r"хостес", re.I), 4, "hostess"),
    (re.compile(r"приват\w*\s*(?:кабинет|комнат|услуг)", re.I), 3, "privat"),
    (re.compile(r"(?:это\s+)?не\s+баня\s+а\b|не\s+баня,?\s+а\b", re.I), 3, "ne_banya"),
    (re.compile(r"сауна[-\s]?клуб", re.I), 3, "sauna_klub_rev"),
    (re.compile(r"только\s+(?:пить|для\s+пьян)|гулянк\w*\s+и\s+вс[её]|пьянк\w+\s+а\s+не\s+бан", re.I), 3, "party_only"),
]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def title_reasons(title: str | None, description: str | None) -> list[str]:
    blob = f"{title or ''} {description or ''}".strip()
    reasons: list[str] = []
    t = (title or "").strip()
    if TITLE_AGGREGATOR.match(t):
        reasons.append("title_aggregator")
    if TITLE_HARD.search(blob):
        reasons.append("title_adult_leisure")
    return reasons


def score_review_text(text: str | None) -> tuple[int, list[str]]:
    t = text or ""
    if not t.strip():
        return 0, []
    score = 0
    tags: list[str] = []
    for pat, weight, tag in REVIEW_RULES:
        if pat.search(t):
            score += weight
            tags.append(tag)
    return score, tags


def collect_review_scores(
    con: sqlite3.Connection,
) -> dict[int, dict]:
    """spot_id → {score, tags, n_flagged, n_reviews}."""
    out: dict[int, dict] = defaultdict(
        lambda: {"score": 0, "tags": [], "n_flagged": 0, "n_reviews": 0}
    )
    for r in con.execute(
        "SELECT spot_id, text FROM banya_reviews "
        "WHERE status IN ('approved','pending') AND text IS NOT NULL AND TRIM(text) != ''"
    ):
        sid = int(r["spot_id"])
        out[sid]["n_reviews"] += 1
        sc, tags = score_review_text(r["text"])
        if sc:
            out[sid]["score"] += sc
            out[sid]["n_flagged"] += 1
            out[sid]["tags"].extend(tags)
    return out


def candidates(
    con: sqlite3.Connection,
    regions: list[str] | None,
    min_review_score: int,
    statuses: tuple[str, ...] = ("published", "draft"),
) -> list[dict]:
    rev = collect_review_scores(con)
    where = [f"status IN ({','.join('?' * len(statuses))})"]
    params: list = list(statuses)
    if regions:
        where.append(f"region IN ({','.join('?' * len(regions))})")
        params.extend(regions)

    rows = con.execute(
        f"SELECT id, title, description, status, region, city, phone "
        f"FROM banya_spots WHERE {' AND '.join(where)} ORDER BY region, id",
        params,
    ).fetchall()

    found: list[dict] = []
    for r in rows:
        reasons = title_reasons(r["title"], r["description"])
        rv = rev.get(int(r["id"]), {})
        rscore = int(rv.get("score") or 0)
        if rscore >= min_review_score:
            reasons.append(f"reviews_score={rscore}")
            # уникальные теги
            tags = sorted(set(rv.get("tags") or []))
            if tags:
                reasons.append("rev:" + ",".join(tags[:8]))
        if not reasons:
            continue
        found.append(
            {
                "id": int(r["id"]),
                "title": r["title"],
                "status": r["status"],
                "region": r["region"],
                "city": r["city"],
                "phone": (r["phone"] or "").strip(),
                "reasons": reasons,
                "review_score": rscore,
                "review_flagged": int(rv.get("n_flagged") or 0),
                "review_total": int(rv.get("n_reviews") or 0),
            }
        )
    return found


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--show", action="store_true", help="только показать (по умолчанию)")
    p.add_argument("--apply", action="store_true", help="status=hidden")
    p.add_argument(
        "--region",
        default="",
        help="коды через запятую, напр. MSK,MO,SPB,LO (пусто = все)",
    )
    p.add_argument(
        "--min-review-score",
        type=int,
        default=4,
        help="порог суммы весов по отзывам (по умолчанию 4)",
    )
    p.add_argument(
        "--include-hidden",
        action="store_true",
        help="также сканировать уже hidden (для отчёта)",
    )
    args = p.parse_args(argv)
    if not args.apply:
        args.show = True

    regions = [x.strip().upper() for x in args.region.split(",") if x.strip()]
    statuses: tuple[str, ...] = ("published", "draft", "hidden") if args.include_hidden else ("published", "draft")

    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=60000")

    found = candidates(con, regions or None, args.min_review_score, statuses)
    by_status: dict[str, int] = defaultdict(int)
    by_region: dict[str, int] = defaultdict(int)
    for f in found:
        by_status[f["status"]] += 1
        by_region[f["region"] or "?"] += 1

    print(f"Кандидатов на hide: {len(found)}")
    print("по статусу:", dict(by_status))
    print("по региону:", dict(sorted(by_region.items())))
    print()
    for f in found[:40]:
        ph = "☎" if f["phone"] else "—"
        print(
            f"  #{f['id']:<5} [{f['status'][0]}] {f['region'] or '-':<4} {ph}  "
            f"{(f['title'] or '')[:50]!r}"
        )
        print(f"         → {', '.join(f['reasons'])}")
    if len(found) > 40:
        print(f"  …+{len(found) - 40} ещё")

    if not args.apply:
        print("\ndry-run. Запусти с --apply, чтобы скрыть.")
        con.close()
        return 0

    ids = [f["id"] for f in found if f["status"] != "hidden"]
    if not ids:
        print("нечего скрывать (уже hidden или пусто).")
        con.close()
        return 0

    now = _now()
    ph = ",".join("?" * len(ids))
    con.execute(
        f"UPDATE banya_spots SET status='hidden', updated_at=? WHERE id IN ({ph}) "
        f"AND status != 'hidden'",
        [now, *ids],
    )
    con.commit()
    print(f"\nhidden: {len(ids)}")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fp:
        for f in found:
            if f["id"] not in ids and f["status"] == "hidden":
                continue
            if f["id"] not in ids:
                continue
            fp.write(
                json.dumps({"ts": now, **f}, ensure_ascii=False) + "\n"
            )
    print(f"лог: {LOG_PATH}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
