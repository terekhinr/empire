#!/usr/bin/env python3
"""Обратное геокодирование через Nominatim — заполняет city для бань без него.

Использование:
    python tools/parsers/nominatim_geocode.py             # все без city, лимит 200
    python tools/parsers/nominatim_geocode.py --limit 50  # первые 50
    python tools/parsers/nominatim_geocode.py --region MO # только МО без city
    python tools/parsers/nominatim_geocode.py --dry       # просто показать

Соблюдаем Nominatim Usage Policy:
  * UA с контактным email
  * не больше 1 req/sec
  * accept-language=ru
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "empire.db"

UA = "GdeParBot/1.0 (+https://gdepar.ru; info@gdepar.ru)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
PAUSE_SEC = 1.1  # >1 сек, чтобы быть «гражданином» Nominatim


def reverse(lat: str, lon: str) -> dict | None:
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "accept-language": "ru",
        "zoom": "14",
        "addressdetails": "1",
    }
    url = NOMINATIM_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ! Nominatim error: {e}", file=sys.stderr)
        return None


def extract_city(payload: dict) -> str | None:
    addr = (payload or {}).get("address") or {}
    # Приоритет: city -> town -> village -> municipality -> county -> suburb -> hamlet
    for key in ("city", "town", "village", "municipality", "county", "suburb", "hamlet"):
        v = addr.get(key)
        if v:
            return v.strip()
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default=None, help="MO|SPB|MSK|LO")
    parser.add_argument("--limit", type=int, default=200, help="максимум точек за прогон")
    parser.add_argument("--dry", action="store_true", help="не писать в БД")
    args = parser.parse_args(argv)

    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    where = ["(city IS NULL OR city = '')", "lat IS NOT NULL", "lon IS NOT NULL"]
    params: list = []
    if args.region:
        where.append("region = ?")
        params.append(args.region.upper())
    rows = con.execute(
        f"SELECT id, title, lat, lon, region FROM banya_spots "
        f"WHERE {' AND '.join(where)} LIMIT ?",
        params + [args.limit],
    ).fetchall()

    if not rows:
        print("Все целевые строки уже с city.")
        return 0

    print(f"Обходим {len(rows)} точек (Nominatim, ~{len(rows) * PAUSE_SEC:.0f} сек)…")
    updated = skipped = 0
    for sid, title, lat, lon, region in rows:
        payload = reverse(lat, lon)
        time.sleep(PAUSE_SEC)
        city = extract_city(payload)
        if not city:
            print(f"  - #{sid:4d} {title[:30]:30s} ({lat},{lon}) — город не найден")
            skipped += 1
            continue
        print(f"  + #{sid:4d} {title[:30]:30s} → {city}")
        if args.dry:
            continue
        now = datetime.utcnow().isoformat(timespec="seconds")
        con.execute(
            "UPDATE banya_spots SET city = ?, updated_at = ? WHERE id = ?",
            (city, now, sid),
        )
        updated += 1
    con.commit()
    con.close()
    print(f"--- Готово. обновлено={updated}, пропущено={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
