#!/usr/bin/env python3
"""Парсер общественных бань из OpenStreetMap (Overpass API).

Идея: даём «остов» точек по регионам (МО, СПб, Урал, Сибирь, ДВ…). Все записи
попадают в `banya_spots` со `status='draft'`. На сайт идут только опубликованные
(через TG-команду `/banya pub` / pubauto).

Запуск:
    python tools/parsers/osm_banyas.py                 # МО + СПб (дефолт)
    python tools/parsers/osm_banyas.py --regions MO,SPB,LO,MSK
    python tools/parsers/osm_banyas.py --regions URAL,SIB,FAR_EAST
    python tools/parsers/osm_banyas.py --regions RU_ALL --sleep 12
    python tools/parsers/osm_banyas.py --dry           # только посмотреть, не писать
    ./scripts/run_osm_ru_all.sh                        # вся РФ → logs/osm_ru_all.log

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
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "empire.db"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.banya_regions import (
    REGIONS,
    REGION_AREA_ISOS,
    REGION_AREA_NAME,
    REGION_FALLBACK_CITY,
    expand_region_tokens,
)
from tools.banya_schema_mvp import ensure_banya_mvp_schema

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
UA = "GdeParBot/1.0 (+https://gdepar.ru; info@gdepar.ru)"
TIMEOUT = 90
OVERPASS_RETRY_WAITS = (20, 45, 90, 120, 180, 240)

# Общая часть: что тянем внутри area `.a`
_OVERPASS_NWR = (
    '('
    '  nwr["leisure"="sauna"](area.a);'
    '  nwr["amenity"="public_bath"](area.a);'
    '  nwr["amenity"="sauna"](area.a);'
    '  nwr["building"="sauna"](area.a);'
    '  nwr["bath:type"="banya"](area.a);'
    '  nwr["bath:type"="sauna"](area.a);'
    '  nwr["bath:type"="hammam"](area.a);'
    '  nwr["building"="bath"]["name"](area.a);'
    ');'
    'out center;'
)

OVERPASS_QUERY_ISO = (
    '[out:json][timeout:{timeout}];'
    'area["ISO3166-2"="{iso}"]->.a;'
    + _OVERPASS_NWR
)

OVERPASS_QUERY_NAME = (
    '[out:json][timeout:{timeout}];'
    'area["name"="{name}"]["admin_level"="4"]->.a;'
    + _OVERPASS_NWR
)

# Что отметаем сразу (явные частные сауны, не относящиеся к общественным баням):
NEG_NAME_PATTERNS = (
    re.compile(r"\bпринадлежит\b", re.I),
)
# Слова, по которым НЕ публикуем (модерация всё равно решит, но это явные «мимо»):
NEG_TAG_VALUES = {
    "private", "yes-private", "members_only",
}

# Безымянные объекты: только «сильные» теги → синтетическое имя (иначе шум дач).
_NAME_FALLBACK_BY_TAG = (
    (("amenity", "public_bath"), "Общественная баня"),
    (("leisure", "sauna"), "Сауна"),
    (("amenity", "sauna"), "Сауна"),
    (("bath:type", "banya"), "Баня"),
    (("bath:type", "hammam"), "Хаммам"),
    (("bath:type", "sauna"), "Сауна"),
)


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


def _overpass_http_error(exc: urllib.error.HTTPError) -> bool:
    return exc.code in (429, 502, 503, 504)


def _query_overpass_raw(query: str) -> list[dict]:
    body = urllib.parse.urlencode({"data": query}).encode()
    last_err: Exception | None = None
    for attempt, wait in enumerate(OVERPASS_RETRY_WAITS):
        url = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT + 10) as r:
                return json.loads(r.read()).get("elements", [])
        except urllib.error.HTTPError as e:
            last_err = e
            if _overpass_http_error(e) and attempt + 1 < len(OVERPASS_RETRY_WAITS):
                print(
                    f"  Overpass {e.code} ({url}), пауза {wait} с…",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            if attempt + 1 < len(OVERPASS_RETRY_WAITS):
                print(f"  Overpass сеть ({e}), пауза {wait} с…", file=sys.stderr, flush=True)
                time.sleep(wait)
                continue
            raise
    if last_err:
        raise last_err
    return []


def _dedupe_elements(elements: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for el in elements:
        key = (el.get("type"), el.get("id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(el)
    return out


def query_overpass_for_region(rcode: str) -> list[dict]:
    """Overpass по ISO (+альтернативы) и при необходимости по name admin_level=4."""
    iso_primary, _label = REGIONS[rcode]
    isos = list(REGION_AREA_ISOS.get(rcode, (iso_primary,)))
    if iso_primary not in isos:
        isos.insert(0, iso_primary)

    best: list[dict] = []
    errors = 0
    last_err: Exception | None = None
    for iso in isos:
        q = OVERPASS_QUERY_ISO.format(iso=iso, timeout=TIMEOUT)
        try:
            els = _query_overpass_raw(q)
        except Exception as e:
            last_err = e
            errors += 1
            print(f"  ISO {iso}: ошибка {e}", file=sys.stderr, flush=True)
            continue
        print(f"  ISO {iso}: {len(els)} объектов", flush=True)
        if len(els) > len(best):
            best = els
        if els:
            break

    if not best:
        name = REGION_AREA_NAME.get(rcode)
        if name:
            q = OVERPASS_QUERY_NAME.format(name=name, timeout=TIMEOUT)
            try:
                els = _query_overpass_raw(q)
                print(f"  name={name!r}: {len(els)} объектов", flush=True)
                best = els
            except Exception as e:
                last_err = e
                errors += 1
                print(f"  name={name!r}: ошибка {e}", file=sys.stderr, flush=True)

    if not best and errors and last_err is not None and errors >= len(isos):
        # Все area-селекторы упали сетью — не маскируем как «пустой регион».
        raise last_err
    return _dedupe_elements(best)


def query_overpass(iso: str) -> list[dict]:
    """Совместимость: один ISO-код."""
    return _query_overpass_raw(OVERPASS_QUERY_ISO.format(iso=iso, timeout=TIMEOUT))


def _resolve_name(tags: dict) -> str | None:
    name = (tags.get("name") or tags.get("name:ru") or tags.get("alt_name") or "").strip()
    if name:
        return name
    # building=bath / building=sauna без имени — почти всегда частная дача
    if tags.get("building") in {"bath", "sauna"} and tags.get("amenity") not in {
        "public_bath", "sauna",
    } and tags.get("leisure") != "sauna":
        return None
    for (k, v), label in _NAME_FALLBACK_BY_TAG:
        if tags.get(k) == v:
            return label
    return None


def _resolve_city(tags: dict, fallback_city: str | None) -> str:
    city = (
        tags.get("addr:city")
        or tags.get("addr:town")
        or tags.get("addr:village")
        or tags.get("addr:hamlet")
        or tags.get("addr:place")
        or tags.get("addr:suburb")
        or fallback_city
        or ""
    ).strip()
    low = city.lower()
    if low in {"saint petersburg", "st petersburg", "st. petersburg"}:
        return "Санкт-Петербург"
    if low in {"moscow", "moskva"}:
        return "Москва"
    return city


def osm_to_spot(el: dict, fallback_city: str | None, region_code: str) -> dict | None:
    """Привести элемент Overpass к словарю BanyaSpot. Возвращает None если объект отбраковали."""
    osm_id = el.get("id")
    tags = el.get("tags", {}) or {}
    if not osm_id or not tags:
        return None
    name = _resolve_name(tags)
    if not name:
        return None
    for pat in NEG_NAME_PATTERNS:
        if pat.search(name):
            return None
    # Gdepar: общественные/достойные бани, не VIP-сауны и безымянный leisure=sauna.
    # Оставляем public_bath / bath:type=banya и всё, где в имени есть «бан».
    _is_public_bath = tags.get("amenity") == "public_bath" or tags.get("bath:type") == "banya"
    _name_l = name.casefold()
    _has_banya_word = "бан" in _name_l
    _sauna_tag = (
        tags.get("leisure") == "sauna"
        or tags.get("amenity") == "sauna"
        or tags.get("building") == "sauna"
        or tags.get("bath:type") == "sauna"
    )
    if not _is_public_bath and not _has_banya_word and _sauna_tag:
        return None
    if re.fullmatch(r"саун[аы]?", _name_l):
        return None
    # Координаты: для node — lat/lon, для way/relation — center.lat/lon
    lat = el.get("lat")
    lon = el.get("lon")
    if (lat is None or lon is None) and isinstance(el.get("center"), dict):
        lat = el["center"].get("lat")
        lon = el["center"].get("lon")
    if lat is None or lon is None:
        return None

    city = _resolve_city(tags, fallback_city)

    street = (tags.get("addr:street") or "").strip()
    house = (tags.get("addr:housenumber") or "").strip()
    address_parts = [p for p in (street, house) if p]
    address = ", ".join(address_parts) if address_parts else ""

    # Сайт/телефон бывают в разных тегах
    site_url = (
        tags.get("website")
        or tags.get("contact:website")
        or tags.get("url")
        or ""
    ).strip() or None
    phone = (
        tags.get("phone")
        or tags.get("contact:phone")
        or tags.get("contact:mobile")
        or ""
    ).strip() or None

    # heating: пытаемся вытащить из подсказок, иначе unknown
    heating = "unknown"
    fuel = (tags.get("fuel") or tags.get("sauna:fuel") or "").lower()
    if "wood" in fuel or fuel in {"firewood", "древесина"}:
        heating = "wood"
    elif "electric" in fuel or "электро" in fuel:
        heating = "electric"
    elif tags.get("sauna:wood_stove") == "yes":
        heating = "wood"

    access = (tags.get("access") or "").lower()
    if access in NEG_TAG_VALUES:
        return None
    kind = "public" if tags.get("amenity") == "public_bath" else "public"

    tags_out = []
    if tags.get("leisure") == "sauna" or tags.get("building") == "sauna":
        tags_out.append("сауна")
    if tags.get("amenity") == "public_bath" or tags.get("bath:type") == "banya":
        tags_out.append("общественные")
    if tags.get("bath:type") == "hammam":
        tags_out.append("хаммам")
    if heating == "wood":
        tags_out.append("дровяные")

    description = (tags.get("description") or tags.get("description:ru") or "").strip() or None

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
    now = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
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


def _ingest_region(
    con: sqlite3.Connection | None,
    rcode: str,
    *,
    dry: bool,
    limit: int,
    total: dict,
) -> bool:
    """True если Overpass ответил; False при сетевой/API ошибке."""
    iso, label = REGIONS[rcode]
    fallback_city = REGION_FALLBACK_CITY.get(rcode)
    print(f"\n=== {label}  (ISO {iso}) ===", flush=True)
    try:
        elements = query_overpass_for_region(rcode)
    except Exception as e:
        print(f"  Overpass упал: {e}", file=sys.stderr, flush=True)
        total["failed_regions"] += 1
        return False
    total["queried"] += len(elements)
    if limit:
        elements = elements[:limit]
    kept_here = 0
    for el in elements:
        spot = osm_to_spot(el, fallback_city, rcode)
        if not spot:
            total["skipped"] += 1
            continue
        total["kept"] += 1
        kept_here += 1
        if dry:
            print(f"  + {spot['title']:40s}  {spot['city'] or '—':22s}  {spot['lat']},{spot['lon']}")
            continue
        assert con is not None
        outcome = upsert(con, spot)
        total[outcome] += 1
    print(f"  OSM: {len(elements)} → keep {kept_here}", flush=True)
    if con is not None and not dry:
        con.commit()
    return True


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="OSM-парсер общественных бань.")
    parser.add_argument(
        "--regions", default="MO,SPB",
        help="через запятую: MO,SPB, EUROPE_RU, RU_ALL, URAL, SIB, FAR_EAST, CFO… (по умолчанию MO,SPB)",
    )
    parser.add_argument("--dry", action="store_true", help="только показать, не писать в БД")
    parser.add_argument("--limit", type=int, default=0, help="ограничить число объектов на регион (для отладки)")
    parser.add_argument(
        "--sleep", type=float, default=10.0,
        help="пауза между областями, сек (по умолчанию 10; для RU_ALL лучше 12–15)",
    )
    parser.add_argument(
        "--retry-failed", action="store_true", default=True,
        help="повторно запросить регионы с ошибкой Overpass (по умолчанию вкл.)",
    )
    parser.add_argument(
        "--no-retry-failed", action="store_false", dest="retry_failed",
        help="не ретраить упавшие регионы в конце прогона",
    )
    args = parser.parse_args(argv)

    regs = expand_region_tokens([r for r in args.regions.split(",") if r.strip()])
    unknown = [r for r in regs if r not in REGIONS]
    if unknown:
        print(f"Неизвестные регионы: {unknown}. Доступно: {list(REGIONS)}", file=sys.stderr)
        return 2

    con: sqlite3.Connection | None = None
    if not args.dry:
        con = sqlite3.connect(str(DB_PATH))
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=30000")
        ensure_schema(con)
        ensure_banya_mvp_schema(con)

    total = {"queried": 0, "kept": 0, "created": 0, "updated": 0, "skipped": 0, "failed_regions": 0}
    failed: list[str] = []
    for i, rcode in enumerate(regs):
        ok = _ingest_region(con, rcode, dry=args.dry, limit=args.limit, total=total)
        if not ok:
            failed.append(rcode)
        if i + 1 < len(regs) or (failed and args.retry_failed):
            time.sleep(max(0.0, args.sleep))

    if failed and args.retry_failed:
        print(f"\n=== Ретрай упавших ({len(failed)}): {','.join(failed)} ===", flush=True)
        time.sleep(max(args.sleep, 30.0))
        still: list[str] = []
        for i, rcode in enumerate(failed):
            ok = _ingest_region(con, rcode, dry=args.dry, limit=args.limit, total=total)
            if not ok:
                still.append(rcode)
            if i + 1 < len(failed):
                time.sleep(max(args.sleep, 15.0))
        # failed_regions считался с двойным инкрементом при ретрае — нормализуем
        total["failed_regions"] = len(still)
        failed = still
    else:
        total["failed_regions"] = len(failed)

    if failed:
        print(f"\n--- Пропущенные регионы ({len(failed)}): {','.join(failed)} ---", flush=True)
        print("  Повтор: python tools/parsers/osm_banyas.py --regions " + ",".join(failed), flush=True)

    if con is not None:
        con.commit()
        con.close()

    print("\n--- ИТОГ ---", flush=True)
    print(f"  Overpass отдал:  {total['queried']}", flush=True)
    print(f"  Подошло:         {total['kept']}", flush=True)
    print(f"  Пропущено:       {total['skipped']}", flush=True)
    if not args.dry:
        print(f"  Новых записей:   {total['created']}", flush=True)
        print(f"  Обновлено:       {total['updated']}", flush=True)
        print(f"  Регионов с ошибкой: {len(failed)}", flush=True)
    else:
        print("  (dry-run: ничего не писали в БД)", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
