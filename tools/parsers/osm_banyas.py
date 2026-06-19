#!/usr/bin/env python3
"""Парсер общественных бань из OpenStreetMap (Overpass API).

Идея: даём «остов» точек по регионам (МО, СПб, ...). Все записи попадают
в `banya_spots` со `status='draft'`. На сайт идут только опубликованные
(через TG-команду `/banya pub`).

Запуск:
    python tools/parsers/osm_banyas.py                 # МО + СПб (дефолт)
    python tools/parsers/osm_banyas.py --regions MO    # только МО
    python tools/parsers/osm_banyas.py --regions MO,SPB,LO,MSK
    python tools/parsers/osm_banyas.py --dry           # только посмотреть, не писать

Скрипт автономен — не импортирует main.py (нет HF/torch и др.).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "empire.db"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.banya_regions import REGIONS, REGION_FALLBACK_CITY, expand_region_tokens

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
UA = "GdeParBot/1.0 (+https://gdepar.ru; info@gdepar.ru)"
TIMEOUT = 90

# Что считаем «баней» в OSM:
#   leisure=sauna             — финские/русские сауны и бани (основной тег)
#   amenity=public_bath       — публичные бани (более редкий тег)
#   building=sauna            — встречается, но без 'leisure' даёт мусор; включаем мягко
OVERPASS_QUERY_TEMPLATE = (
    '[out:json][timeout:{timeout}];'
    'area["ISO3166-2"="{iso}"]->.a;'
    '('
    '  nwr["leisure"="sauna"](area.a);'
    '  nwr["amenity"="public_bath"](area.a);'
    '  nwr["amenity"="sauna"](area.a);'
    ');'
    'out center 500;'
)

# Что отметаем сразу (явные частные сауны, не относящиеся к общественным баням):
NEG_NAME_PATTERNS = (
    re.compile(r"\bпринадлежит\b", re.I),
)
# Слова, по которым НЕ публикуем (модерация всё равно решит, но это явные «мимо»):
NEG_TAG_VALUES = {
    "private", "yes-private", "members_only",
}


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60]


def slugify_ru(title: str, city: str | None, osm_id: int) -> str:
    """Slug на основе латинизированного имени + osm_id, чтобы был уникальным."""
    base = slugify(title or "")
    if not base:
        base = "banya"
    # Подмешиваем последние 6 цифр OSM id — дёшево и стабильно уникально.
    return f"{base}-{osm_id % 1_000_000:06d}"


def query_overpass(iso: str) -> list[dict]:
    q = OVERPASS_QUERY_TEMPLATE.format(iso=iso, timeout=TIMEOUT)
    body = urllib.parse.urlencode({"data": q}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=body, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT + 10) as r:
        return json.loads(r.read()).get("elements", [])


def osm_to_spot(el: dict, fallback_city: str | None, region_code: str) -> dict | None:
    """Привести элемент Overpass к словарю BanyaSpot. Возвращает None если объект отбраковали."""
    osm_id = el.get("id")
    tags = el.get("tags", {}) or {}
    if not osm_id or not tags:
        return None
    name = (tags.get("name") or tags.get("name:ru") or "").strip()
    if not name:
        return None
    for pat in NEG_NAME_PATTERNS:
        if pat.search(name):
            return None
    # Координаты: для node — lat/lon, для way/relation — center.lat/lon
    lat = el.get("lat")
    lon = el.get("lon")
    if (lat is None or lon is None) and isinstance(el.get("center"), dict):
        lat = el["center"].get("lat")
        lon = el["center"].get("lon")
    if lat is None or lon is None:
        return None

    city = (tags.get("addr:city") or tags.get("addr:suburb") or fallback_city or "").strip()
    # Питер OSM-тегирует как «Saint Petersburg»/«Санкт-Петербург»; нормализуем.
    if city.lower() in {"saint petersburg", "st petersburg", "st. petersburg"}:
        city = "Санкт-Петербург"
    # Если для МО город всё ещё пустой — оставим пустым, модерация подскажет.

    street = (tags.get("addr:street") or "").strip()
    house = (tags.get("addr:housenumber") or "").strip()
    address_parts = [p for p in (street, house) if p]
    address = ", ".join(address_parts) if address_parts else ""

    # Сайт/телефон бывают в разных тегах
    site_url = (tags.get("website") or tags.get("contact:website") or "").strip() or None
    phone = (tags.get("phone") or tags.get("contact:phone") or "").strip() or None

    # heating: пытаемся вытащить из подсказок, иначе unknown
    heating = "unknown"
    fuel = (tags.get("fuel") or "").lower()
    if "wood" in fuel:
        heating = "wood"
    elif "electric" in fuel:
        heating = "electric"
    elif tags.get("sauna:wood_stove") == "yes":
        heating = "wood"

    # kind: public_bath → 'public', sauna без access — 'public' по умолчанию, но
    # если access=private — это уже точно частная.
    access = (tags.get("access") or "").lower()
    if access in NEG_TAG_VALUES:
        return None
    kind = "public" if tags.get("amenity") == "public_bath" else "public"

    tags_out = []
    if tags.get("leisure") == "sauna":
        tags_out.append("сауна")
    if tags.get("amenity") == "public_bath":
        tags_out.append("общественные")
    if heating == "wood":
        tags_out.append("дровяные")

    description = (tags.get("description") or "").strip() or None

    return {
        "_osm_id": osm_id,
        "slug": slugify_ru(name, city, osm_id),
        "title": name,
        "city": city or None,
        "region": region_code,
        "address": address or None,
        "lat": f"{lat:.6f}",
        "lon": f"{lon:.6f}",
        "heating": heating,
        "kind": kind,
        "site_url": site_url,
        "phone": phone,
        "tags_json": json.dumps(tags_out, ensure_ascii=False) if tags_out else None,
        "description": description,
    }


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS banya_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE,
            title TEXT,
            city TEXT,
            address TEXT,
            lat TEXT,
            lon TEXT,
            heating TEXT,
            kind TEXT,
            site_url TEXT,
            phone TEXT,
            yandex_url TEXT,
            twogis_url TEXT,
            cover_url TEXT,
            description TEXT,
            clips_json TEXT,
            tags_json TEXT,
            visited INTEGER DEFAULT 0,
            status TEXT DEFAULT 'draft',
            rating_avg TEXT,
            reviews_total INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_banya_spots_city   ON banya_spots(city);
        CREATE INDEX IF NOT EXISTS idx_banya_spots_status ON banya_spots(status);
        """
    )
    # Поле для дедупа по OSM id — добавляем идемпотентно.
    for col, ddl in (("osm_id", "TEXT"), ("region", "TEXT")):
        try:
            con.execute(f"ALTER TABLE banya_spots ADD COLUMN {col} {ddl}")
        except sqlite3.OperationalError:
            pass  # колонка уже есть
    con.execute("CREATE INDEX IF NOT EXISTS idx_banya_spots_osm_id ON banya_spots(osm_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_banya_spots_region ON banya_spots(region)")
    con.commit()


def upsert(con: sqlite3.Connection, spot: dict) -> str:
    """Upsert по osm_id; если по slug совпало с ранее заведённым — обновляем,
    но НЕ перезатираем уже заполненные руками поля."""
    cur = con.cursor()
    now = datetime.utcnow().isoformat(timespec="seconds")
    osm_id_str = str(spot["_osm_id"])

    row = cur.execute(
        "SELECT id, status, title, city, address, site_url, phone, description "
        "FROM banya_spots WHERE osm_id = ? OR slug = ?",
        (osm_id_str, spot["slug"]),
    ).fetchone()

    if row:
        # Обновляем только пустые поля (не затираем ручную правку).
        sid, status, title, city, address, site_url, phone, descr = row
        sets = {
            "osm_id": osm_id_str,
            "region": spot["region"],
            "lat": spot["lat"], "lon": spot["lon"],
            "heating": spot["heating"], "kind": spot["kind"],
            "tags_json": spot["tags_json"],
        }
        if not title:
            sets["title"] = spot["title"]
        if not city:
            sets["city"] = spot["city"]
        if not address:
            sets["address"] = spot["address"]
        if not site_url and spot["site_url"]:
            sets["site_url"] = spot["site_url"]
        if not phone and spot["phone"]:
            sets["phone"] = spot["phone"]
        if not descr and spot["description"]:
            sets["description"] = spot["description"]
        cols = ", ".join(f"{k} = ?" for k in sets)
        cur.execute(
            f"UPDATE banya_spots SET {cols}, updated_at = ? WHERE id = ?",
            list(sets.values()) + [now, sid],
        )
        return "updated"

    fields = {
        "osm_id": osm_id_str,
        "region": spot["region"],
        "slug": spot["slug"],
        "title": spot["title"],
        "city": spot["city"],
        "address": spot["address"],
        "lat": spot["lat"], "lon": spot["lon"],
        "heating": spot["heating"], "kind": spot["kind"],
        "site_url": spot["site_url"], "phone": spot["phone"],
        "tags_json": spot["tags_json"], "description": spot["description"],
        "status": "draft",
        "created_at": now, "updated_at": now,
    }
    cols = ", ".join(fields.keys())
    placeholders = ", ".join(["?"] * len(fields))
    cur.execute(
        f"INSERT INTO banya_spots ({cols}) VALUES ({placeholders})",
        list(fields.values()),
    )
    return "created"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="OSM-парсер общественных бань.")
    parser.add_argument(
        "--regions", default="MO,SPB",
        help="через запятую: MO,SPB,MSK,LO,CFO,GDEPAR или код области (по умолчанию MO,SPB)",
    )
    parser.add_argument("--dry", action="store_true", help="только показать, не писать в БД")
    parser.add_argument("--limit", type=int, default=0, help="ограничить число объектов на регион (для отладки)")
    args = parser.parse_args(argv)

    regs = expand_region_tokens([r for r in args.regions.split(",") if r.strip()])
    unknown = [r for r in regs if r not in REGIONS]
    if unknown:
        print(f"Неизвестные регионы: {unknown}. Доступно: {list(REGIONS)}", file=sys.stderr)
        return 2

    con = sqlite3.connect(str(DB_PATH))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    if not args.dry:
        ensure_schema(con)

    total = {"queried": 0, "kept": 0, "created": 0, "updated": 0, "skipped": 0}
    for rcode in regs:
        iso, label = REGIONS[rcode]
        fallback_city = REGION_FALLBACK_CITY.get(rcode)
        print(f"\n=== {label}  (ISO {iso}) ===")
        try:
            elements = query_overpass(iso)
        except Exception as e:
            print(f"  Overpass упал: {e}", file=sys.stderr)
            continue
        total["queried"] += len(elements)
        if args.limit:
            elements = elements[: args.limit]
        for el in elements:
            spot = osm_to_spot(el, fallback_city, rcode)
            if not spot:
                total["skipped"] += 1
                continue
            total["kept"] += 1
            if args.dry:
                print(f"  + {spot['title']:40s}  {spot['city'] or '—':22s}  {spot['lat']},{spot['lon']}")
                continue
            outcome = upsert(con, spot)
            total[outcome] += 1
        time.sleep(3.0)  # Пауза между областями (Overpass 429/504)

    if not args.dry:
        con.commit()
    con.close()

    print("\n--- ИТОГ ---")
    print(f"  Overpass отдал:  {total['queried']}")
    print(f"  Подошло:         {total['kept']}")
    print(f"  Пропущено:       {total['skipped']}")
    if not args.dry:
        print(f"  Новых записей:   {total['created']}")
        print(f"  Обновлено:       {total['updated']}")
    else:
        print("  (dry-run: ничего не писали в БД)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
