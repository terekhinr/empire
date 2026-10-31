"""Качество каталога бань (аудит R7 / 21_GEMINI_R7.md).

R7: массовый парсинг = балласт; фокус FLAGSHIP (MSK/MO/SPB/LO),
телефоны + живые точки с трафиком (много отзывов на Яндексе).

Пороги через env (дефолты под «актуальная баня с посещаемостью», R7):
  BANYA_QUALITY_REGIONS=MSK,MO,SPB,LO
  BANYA_MIN_REVIEWS=50          # reviews_total с Яндекса (посещаемость)
  BANYA_MIN_RATING=4.0
  BANYA_REVIEW_MAX_AGE_DAYS=365 # не сохранять отзыв старше года
  BANYA_SPOT_STALE_DAYS=270     # новейший отзыв старше ~9 мес → точка «мёртвая»
  BANYA_REQUIRE_PHONE=1         # published без телефона → draft (phone_reveal)

Запуск:
  ./venv/bin/python tools/banya_quality.py --show
  ./venv/bin/python tools/banya_quality.py --apply   # published→draft ниже порога
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "empire.db"

_MONTHS_RU = (
    ("январ", 1),
    ("феврал", 2),
    ("март", 3),
    ("апрел", 4),
    ("мая", 5),
    ("май", 5),
    ("июн", 6),
    ("июл", 7),
    ("август", 8),
    ("сентябр", 9),
    ("октябр", 10),
    ("ноябр", 11),
    ("декабр", 12),
)


def quality_regions() -> tuple[str, ...]:
    raw = os.environ.get("BANYA_QUALITY_REGIONS", "MSK,MO,SPB,LO")
    return tuple(x.strip().upper() for x in raw.split(",") if x.strip())


def min_reviews() -> int:
    return int(os.environ.get("BANYA_MIN_REVIEWS", "50"))


def min_rating() -> float:
    return float(os.environ.get("BANYA_MIN_RATING", "4.0"))


def review_max_age_days() -> int:
    return int(os.environ.get("BANYA_REVIEW_MAX_AGE_DAYS", "365"))


def spot_stale_days() -> int:
    return int(os.environ.get("BANYA_SPOT_STALE_DAYS", "270"))


def require_phone() -> bool:
    raw = os.environ.get("BANYA_REQUIRE_PHONE", "1")
    return raw.lower() in ("1", "true", "yes")


def flagship_region_sql(column: str = "region") -> str:
    regs = quality_regions()
    if not regs:
        return "1=1"
    inner = ", ".join(f"'{r}'" for r in regs)
    return f"{column} IN ({inner})"


def title_looks_like_banya(title: str | None) -> bool:
    t = (title or "").casefold()
    if not t.strip():
        return False
    return "бан" in t


def title_is_sauna_only(title: str | None) -> bool:
    t = (title or "").strip()
    if not t:
        return False
    low = t.casefold()
    return ("саун" in low) and ("бан" not in low)


def parse_review_date(raw: str | None, *, now: datetime | None = None) -> datetime | None:
    """Разбор даты отзыва Яндекса → naive UTC datetime (дата без времени)."""
    if not raw:
        return None
    text = re.sub(r"\s+", " ", str(raw)).strip().casefold()
    if not text:
        return None
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if "сегодня" in text:
        return today
    if "вчера" in text:
        return today - timedelta(days=1)

    m = re.search(
        r"(\d+)\s*(минут|час|день|дня|дней|недел|месяц|год)",
        text,
    )
    if m and "назад" in text:
        n = int(m.group(1))
        unit = m.group(2)
        if unit.startswith("минут") or unit.startswith("час"):
            return today
        if unit.startswith("день") or unit.startswith("дня") or unit.startswith("дней"):
            return today - timedelta(days=n)
        if unit.startswith("недел"):
            return today - timedelta(weeks=n)
        if unit.startswith("месяц"):
            return today - timedelta(days=30 * n)
        if unit.startswith("год"):
            return today - timedelta(days=365 * n)

    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    m = re.search(r"(?:(\d{1,2})\s+)?([а-яё]+)\s+(20\d{2})", text)
    if m:
        day_s, mon_s, year_s = m.group(1), m.group(2), m.group(3)
        month = None
        for prefix, num in _MONTHS_RU:
            if mon_s.startswith(prefix):
                month = num
                break
        if month:
            day = int(day_s) if day_s else 1
            try:
                return datetime(int(year_s), month, day)
            except ValueError:
                pass
    return None


def review_is_fresh(published_at: datetime | None, *, now: datetime | None = None) -> bool:
    if published_at is None:
        return False
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    return (now - published_at).days <= review_max_age_days()


def traffic_ok(
    reviews_total: int | None,
    rating_avg: float | str | None,
    *,
    min_rev: int | None = None,
    min_rat: float | None = None,
    unknown_ok: bool = False,
) -> bool:
    """unknown_ok=True: NULL/0 reviews_total не провал (ещё не refresh с Яндекса)."""
    min_rev = min_reviews() if min_rev is None else min_rev
    min_rat = min_rating() if min_rat is None else min_rat
    try:
        rt = int(reviews_total) if reviews_total is not None else 0
    except (TypeError, ValueError):
        rt = 0
    if reviews_total in (None, "", 0) or rt == 0:
        return bool(unknown_ok)
    if rt < min_rev:
        return False
    if rating_avg in (None, ""):
        return True
    try:
        return float(str(rating_avg).replace(",", ".")) >= min_rat
    except ValueError:
        return True


def _looks_iso(s: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", (s or "").strip()))


def _parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00").split("+")[0][:19])
    except ValueError:
        return None


def newest_review_published_at(con: sqlite3.Connection, spot_id: int) -> datetime | None:
    rows = con.execute(
        "SELECT published_at FROM banya_reviews "
        "WHERE spot_id = ? AND status IN ('approved','pending') "
        "AND published_at IS NOT NULL AND TRIM(published_at) != '' "
        "ORDER BY published_at DESC LIMIT 5",
        (spot_id,),
    ).fetchall()
    best: datetime | None = None
    for (raw,) in rows:
        dt = parse_review_date(raw) if not _looks_iso(str(raw)) else _parse_iso(str(raw))
        if dt and (best is None or dt > best):
            best = dt
    return best


def spot_reviews_fresh(con: sqlite3.Connection, spot_id: int) -> bool | None:
    """True=свежие, False=устарели, None=нет датированных отзывов."""
    newest = newest_review_published_at(con, spot_id)
    if newest is None:
        return None
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return (now - newest).days <= spot_stale_days()


def low_quality_published(con: sqlite3.Connection) -> list[dict]:
    """Published с ИЗВЕСТНЫМ низким трафиком (reviews_total>0 и ниже порога) или сауны.

    reviews_total NULL/0 не трогаем — сначала refresh с Яндекса (иначе Сандуны → draft).
    """
    regs = quality_regions()
    placeholders = ",".join("?" * len(regs))
    rows = con.execute(
        f"SELECT id, title, region, phone, rating_avg, reviews_total, yandex_url "
        f"FROM banya_spots WHERE status = 'published' AND region IN ({placeholders})",
        regs,
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        sid, title, region, phone, rating, rev_total, yurl = r
        reasons: list[str] = []
        if title_is_sauna_only(title):
            reasons.append("sauna_only_title")
        try:
            rt = int(rev_total) if rev_total is not None else 0
        except (TypeError, ValueError):
            rt = 0
        known_count = rt > 0
        if known_count and not traffic_ok(rt, rating):
            reasons.append(f"low_traffic(rev={rev_total},★={rating})")
        if require_phone() and not (phone or "").strip():
            reasons.append("no_phone")
        fresh = spot_reviews_fresh(con, sid)
        if fresh is False and known_count:
            reasons.append("stale_reviews")
        if reasons:
            out.append(
                {
                    "id": sid,
                    "title": title,
                    "region": region,
                    "reviews_total": rev_total,
                    "rating_avg": rating,
                    "reasons": reasons,
                }
            )
    return out


def apply_demote(con: sqlite3.Connection, items: list[dict]) -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    n = 0
    for it in items:
        cur = con.execute(
            "UPDATE banya_spots SET status = 'draft', updated_at = ? "
            "WHERE id = ? AND status = 'published'",
            (now, it["id"]),
        )
        n += cur.rowcount
    con.commit()
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Quality gate каталога бань (R7)")
    ap.add_argument("--show", action="store_true", help="показать кандидатов на demote")
    ap.add_argument("--apply", action="store_true", help="published → draft")
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args(argv)
    if not args.show and not args.apply:
        args.show = True

    con = sqlite3.connect(str(args.db))
    items = low_quality_published(con)
    print(
        f"regions={','.join(quality_regions())} "
        f"min_reviews={min_reviews()} min_rating={min_rating()} "
        f"review_max_age_d={review_max_age_days()} spot_stale_d={spot_stale_days()}"
    )
    print(f"low_quality published: {len(items)}")
    for it in items[:40]:
        print(
            f"  #{it['id']:>4} [{it['region']}] rev={it['reviews_total']} "
            f"★{it['rating_avg']}  {it['title'][:50]}  :: {', '.join(it['reasons'])}"
        )
    if len(items) > 40:
        print(f"  …+{len(items) - 40}")
    if args.apply:
        n = apply_demote(con, items)
        print(f"demoted to draft: {n}")
    else:
        print("dry-run. --apply чтобы перевести в draft.")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
