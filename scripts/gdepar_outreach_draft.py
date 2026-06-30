#!/usr/bin/env python3
"""Черновики outreach для владельцев бань (Gdepar Premium).

Примеры:
  ./venv/bin/python scripts/gdepar_outreach_draft.py --region MO,MSK,SPB --limit 10
  ./venv/bin/python scripts/gdepar_outreach_draft.py --published-only --format csv -o data/gdepar_outreach_queue.csv
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "empire.db"
CANONICAL = "https://gdepar.ru"

WHATSAPP_TEMPLATE = """Добрый день! «Где Пар» — карта бань gdepar.ru

Ваша баня «{title}» уже в каталоге: {card_url}

Считаем лиды: показы телефона и интерес к карточке. База — бесплатно.

Premium (пилот 2 990 ₽/мес): топ в районе {city}, бейдж, приоритет в выдаче.

Прислать отчёт за месяц по вашей карточке? Ответьте «да» — пришлю цифры."""

EMAIL_SUBJECT = "{title} на карте бань — отчёт по заявкам (бесплатно)"

EMAIL_BODY = """Здравствуйте!

Проект «Где Пар» — каталог общественных бань: {canonical}

Ваша баня «{title}» ({city}):
{card_url}

Мы считаем лиды: просмотры карточки, нажатия «показать телефон».

• Бесплатно — карточка + отчёт по лидам
• Premium (пилот) — 2 990 ₽/мес: приоритет в выдаче по {city}, бейдж «Проверено»

Могу прислать цифры за 30 дней — без обязательств.

Где Пар · {canonical}/partners
info@gdepar.ru"""


def card_url(slug: str) -> str:
    return f"{CANONICAL}/banya/{slug}"


def fetch_rows(
    con: sqlite3.Connection,
    regions: list[str] | None,
    published_only: bool,
    limit: int,
) -> list[sqlite3.Row]:
    where = ["(phone IS NOT NULL AND phone != '')"]
    params: list[object] = []
    if regions:
        where.append(f"region IN ({','.join('?' * len(regions))})")
        params.extend(regions)
    if published_only:
        where.append("status = 'published'")
    sql = f"""
        SELECT id, slug, title, city, region, phone, status, partner_tier,
               COALESCE(map_views, 0) AS map_views
        FROM banya_spots
        WHERE {' AND '.join(where)}
        ORDER BY
            CASE status WHEN 'published' THEN 0 ELSE 1 END,
            map_views DESC,
            title
        LIMIT ?
    """
    params.append(limit)
    con.row_factory = sqlite3.Row
    return list(con.execute(sql, params).fetchall())


def print_text(rows: list[sqlite3.Row]) -> None:
    for i, r in enumerate(rows, 1):
        city = r["city"] or r["region"] or "—"
        url = card_url(r["slug"])
        print("=" * 72)
        print(f"#{i}  id={r['id']}  {r['title']}  ({city}, {r['region']})")
        print(f"    tel: {r['phone']}  status={r['status']}  tier={r['partner_tier'] or 'free'}")
        print(f"    {url}")
        print()
        print("--- WhatsApp ---")
        print(WHATSAPP_TEMPLATE.format(title=r["title"], city=city, card_url=url))
        print()
        print("--- Email subject ---")
        print(EMAIL_SUBJECT.format(title=r["title"]))
        print()
        print("--- Email body ---")
        print(EMAIL_BODY.format(title=r["title"], city=city, card_url=url, canonical=CANONICAL))
        print()


def write_csv(rows: list[sqlite3.Row], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "id",
                "title",
                "city",
                "region",
                "phone",
                "status",
                "partner_tier",
                "card_url",
                "whatsapp_draft",
                "email_subject",
            ]
        )
        for r in rows:
            city = r["city"] or r["region"] or ""
            url = card_url(r["slug"])
            w.writerow(
                [
                    r["id"],
                    r["title"],
                    city,
                    r["region"],
                    r["phone"],
                    r["status"],
                    r["partner_tier"] or "free",
                    url,
                    WHATSAPP_TEMPLATE.format(title=r["title"], city=city, card_url=url),
                    EMAIL_SUBJECT.format(title=r["title"]),
                ]
            )
    print(f"Wrote {len(rows)} rows → {path}", file=sys.stderr)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Gdepar Premium outreach drafts")
    p.add_argument("--region", default="MO,MSK,SPB", help="коды через запятую")
    p.add_argument("--published-only", action="store_true")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--format", choices=("text", "csv"), default="text")
    p.add_argument("-o", "--output", type=Path, help="CSV output path")
    args = p.parse_args(argv)

    regions = [x.strip().upper() for x in args.region.split(",") if x.strip()] or None
    con = sqlite3.connect(str(DB_PATH))
    rows = fetch_rows(con, regions, args.published_only, args.limit)
    con.close()

    if not rows:
        print("Нет строк по фильтру.", file=sys.stderr)
        return 1

    if args.format == "csv":
        out = args.output or ROOT / "data" / "gdepar_outreach_queue.csv"
        write_csv(rows, out)
    else:
        print_text(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
