"""Качает public-domain гравюры/живопись русской бани с Викисклада.

Стратегия:
  1) ищем через search по фразам ("баня", "купание", "venik" и т.п.),
  2) для каждой находки берём imageinfo + проверяем лицензию (PD/CC0/CC-BY),
  3) скачиваем превью ~900px, сохраняем slug по pageid.

Запускать локально с правами на сеть:
    python tools/fetch_banya_engravings.py [N]
где N — желаемое число иллюстраций (по умолчанию 10).
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "static" / "gdepar" / "bayki"
OUT_DIR.mkdir(parents=True, exist_ok=True)

API = "https://commons.wikimedia.org/w/api.php"
UA = "GdeParBot/1.0 (+https://gdepar.ru; info@gdepar.ru)"

# Фразы для поиска. Намеренно англоязычные и русские, чтобы максимизировать охват
# исторических работ. Каждая возвращает 10-20 файлов.
QUERIES = [
    "russian banya painting",
    "russian bath painting",
    "Кустодиев баня",
    "Соломаткин баня",
    "Маковский баня",
    "Журавлев купальщица",
    "русская баня живопись",
    "village banya 19th century",
    "banya engraving",
    "russian peasant bath",
]

# Допускаемые лицензии (короткие коды из шаблона LicenseShortName).
ALLOWED_LICENSES = {
    "PD", "Public domain", "PUBLIC DOMAIN",
    "CC0", "CC-PD-Mark",
    "CC BY", "CC BY-SA",
    "CC BY 2.0", "CC BY 3.0", "CC BY 4.0",
    "CC BY-SA 2.0", "CC BY-SA 3.0", "CC BY-SA 4.0",
    "PD-US", "PD-Russia", "PD-Art", "PD-old",
}


def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def http_download(url: str, out: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r, out.open("wb") as f:
        while chunk := r.read(16384):
            f.write(chunk)


def search_files(query: str, limit: int = 20) -> list[str]:
    """Список File:... заголовков."""
    url = (
        API + "?action=query&list=search&srnamespace=6&format=json"
        + f"&srlimit={limit}&srsearch=" + urllib.parse.quote(query)
    )
    try:
        j = http_json(url)
    except Exception:
        return []
    return [s["title"] for s in j.get("query", {}).get("search", []) if s.get("title")]


def file_info(title: str) -> dict | None:
    url = (
        API
        + "?action=query&prop=imageinfo&iiprop=url|mime|extmetadata|size"
        + "&iiurlwidth=900&format=json&titles=" + urllib.parse.quote(title)
    )
    try:
        j = http_json(url)
    except Exception:
        return None
    pages = j.get("query", {}).get("pages", {})
    for _, page in pages.items():
        ii = page.get("imageinfo") or []
        if ii:
            return ii[0]
    return None


def license_ok(info: dict) -> bool:
    meta = info.get("extmetadata") or {}
    short = (meta.get("LicenseShortName") or {}).get("value", "") or ""
    return any(short.startswith(L) or short == L for L in ALLOWED_LICENSES)


def slugify(title: str) -> str:
    s = title.replace("File:", "")
    s = re.sub(r"\.(jpg|jpeg|png|tif|tiff|webp)$", "", s, flags=re.I)
    s = re.sub(r"[^A-Za-z0-9А-Яа-яЁё]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-").lower()
    return s[:80]


def main() -> int:
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    seen: set[str] = set()
    saved = 0
    skipped = 0
    rejected = 0

    for q in QUERIES:
        if saved >= target:
            break
        for title in search_files(q, limit=20):
            if saved >= target:
                break
            if title in seen:
                continue
            seen.add(title)
            info = file_info(title)
            if not info:
                continue
            mime = info.get("mime", "")
            if mime not in {"image/jpeg", "image/png"}:
                continue
            if not license_ok(info):
                rejected += 1
                continue
            src = info.get("thumburl") or info.get("url")
            if not src:
                continue
            slug = slugify(title)
            out = OUT_DIR / f"{slug}.jpg"
            if out.exists() and out.stat().st_size > 5000:
                print(f"= {slug}")
                saved += 1
                continue
            try:
                http_download(src, out)
                print(f"+ {slug} ({out.stat().st_size // 1024} KB)")
                saved += 1
                time.sleep(0.4)
            except Exception as e:
                print(f"! {slug}: {e}")
                skipped += 1
    print(f"---\nготово: {saved} файлов, отброшено по лицензии: {rejected}, ошибки: {skipped}")
    return 0 if saved > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
