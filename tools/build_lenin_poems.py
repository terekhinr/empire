#!/usr/bin/env python3
"""Сборник стихов о Ленине: оглавление книги → чистые тексты из сети/PDF → JSON для постинга."""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import fitz
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lenin_poems_catalog import CATALOG, EXTERNAL_URLS, WORK, _LENINISM_BASE, page_ranges

ROOT = Path(__file__).resolve().parents[1]
POEMS_PDF = ROOT / "data" / "lenin" / "Стихи о Ленине (Школьная библиотека) — 1974.pdf"
OUT = ROOT / "data" / "lenin_poems_curated.json"
REPORT = ROOT / "data" / "lenin_poems_fetch_report.json"

UA = {"User-Agent": "Mozilla/5.0 (compatible; EmpireLeninPoems/1.0)"}
MAX_QUOTE = 900
MIN_QUOTE = 80

_SPACED_RE = re.compile(r"(?<=[А-ЯЁа-яё])\s+(?=[А-ЯЁа-яё]\s)")
_JUNK_RE = re.compile(
    r"[\u0400-\u04FF]{0,2}[^\u0400-\u04FF\u0020-\u007E«»—–\.\,\!\?\:\;\-\(\)\"\'\n]{3,}"
)
_PAGE_NUM_RE = re.compile(r"^\d{1,3}$")


def _norm(s: str) -> str:
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[^а-яa-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_key(author: str, title: str) -> str:
    return f"{_norm(author)}|{_norm(title)[:48]}"


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _clean_poem_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = t.replace("\u00ad", "").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    # убрать разрядку внутри слов: «Д ж а м б у л» → «Джамбул» (только короткие фрагменты)
    lines = []
    for line in t.splitlines():
        if re.fullmatch(r"(?:[А-ЯЁа-яё]\s+){3,}[А-ЯЁа-яё]", line.strip()):
            line = re.sub(r"(?<=[А-ЯЁа-яё])\s+(?=[А-ЯЁа-яё])", "", line)
        lines.append(line)
    t = "\n".join(lines)
    t = re.sub(r"^\d{1,3}\s*$", "", t, flags=re.MULTILINE)
    return t.strip()


def _surname(author: str) -> str:
    parts = re.sub(r"[^а-яёa-z\s]", " ", (author or "").lower()).split()
    return parts[-1] if parts else ""


def _readable(text: str, *, trusted: bool = False) -> bool:
    if len(text) < MIN_QUOTE:
        return False
    if not trusted:
        if "Ленин" not in text and "Ильич" not in text and "Ульянов" not in text:
            return False
    cyr = len(re.findall(r"[а-яА-ЯёЁ]", text))
    if cyr < len(text) * 0.5:
        return False
    if _JUNK_RE.search(text):
        return False
    if re.search(r"(?:[А-ЯЁ]\s+){4,}[А-ЯЁ]", text):
        return False
    return True


def _fix_ocr_starts(text: str) -> str:
    fixes = {
        "огда ": "Когда ",
        "сть ": "Есть ",
        "етроград": "Петроград",
        "I  роснулся": "Проснулся",
        "пять погода": "Опять погода",
        "ого рассказывал": "Того рассказывал",
        "окончив с": "Покончив с",
        "й\n^": "",
    }
    for old, new in fixes.items():
        if text.startswith(old) or f"\n{old}" in text:
            text = text.replace(old, new, 1)
    return text


def _fetch_url(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=25, headers=UA)
        if r.status_code != 200:
            return None
        if "culture.ru/poems/" in url:
            return _parse_culture(r.text)
        if "rustih.ru/" in url:
            return _parse_rustih(r.text)
        if "leninism.su/" in url:
            return _parse_leninism_page(r.text)
        return None
    except requests.RequestException:
        return None


def _parse_rustih(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    el = soup.select_one(".entry-content")
    if not el:
        return None
    text = el.get_text("\n", strip=True)
    for stop in ("Читайте также", "Выбор читателей", "Отзывы", "Поделиться"):
        if stop in text:
            text = text.split(stop)[0].strip()
    return _clean_poem_text(text) if len(text) >= MIN_QUOTE else None


def _parse_culture(html: str) -> str | None:
    nd = BeautifulSoup(html, "lxml").find("script", id="__NEXT_DATA__")
    if not nd or not nd.string:
        return None
    data = json.loads(nd.string)

    def walk(o):
        if isinstance(o, dict):
            for k in ("text", "body", "content"):
                if k in o and isinstance(o[k], str) and len(o[k]) > MIN_QUOTE:
                    return o[k]
            for v in o.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = walk(v)
                if r:
                    return r
        return None

    raw = walk(data)
    if not raw:
        return None
    raw = re.sub(r"(?<=[а-яё])(?=[А-ЯЁ«])", "\n", raw)
    raw = re.sub(r"(?<=[.!?…])(?=[А-ЯЁ«])", "\n", raw)
    return _clean_poem_text(raw)


def _parse_leninism_page(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    content = soup.select_one(".item-page")
    if not content:
        return None
    h3s = [h for h in content.find_all("h3") if h.get_text(strip=True) != "Содержание материала"]
    if len(h3s) < 2:
        return None
    texts = []
    for s in h3s[1].next_siblings:
        if getattr(s, "name", None) in ("p", "div"):
            tx = s.get_text("\n", strip=True)
            if tx:
                texts.append(tx)
    body = "\n".join(texts)
    for stop in ("ВКонтакте", "Одноклассники", "LiveInternet", "©", "Предыдущая", "Следующая", "Назад"):
        if stop in body:
            body = body.split(stop)[0].strip()
    return _clean_poem_text(body) if len(body) >= MIN_QUOTE else None


def fetch_leninism_index() -> list[dict]:
    """Все стихи с leninism.su (?showall=1 — полный сборник)."""
    index: list[dict] = []
    url = f"{_LENINISM_BASE}?showall=1"
    try:
        r = requests.get(url, timeout=40, headers=UA)
    except requests.RequestException:
        return index
    if r.status_code != 200:
        return index
    soup = BeautifulSoup(r.text, "lxml")
    content = soup.select_one(".item-page")
    if not content:
        return index
    h3s = [h for h in content.find_all("h3") if h.get_text(strip=True) != "Содержание материала"]
    i = 0
    while i + 1 < len(h3s):
        author = h3s[i].get_text(strip=True)
        title = h3s[i + 1].get_text(strip=True)
        node = h3s[i + 1]
        texts = []
        for s in node.next_siblings:
            if getattr(s, "name", None) == "h3":
                break
            if getattr(s, "name", None) in ("p", "div"):
                tx = s.get_text("\n", strip=True)
                if tx:
                    texts.append(tx)
        body = "\n".join(texts)
        for stop in ("ВКонтакте", "Одноклассники", "LiveInternet", "©", "Назад", "Вперед"):
            if stop in body:
                body = body.split(stop)[0].strip()
        body = _clean_poem_text(body)
        if len(body) >= MIN_QUOTE:
            index.append(
                {"author": author, "title": title, "text": body, "url": url, "source": "leninism.su"}
            )
        i += 2
    return index


def _match_leninism(item: dict, index: list[dict], hint: str | None = None) -> dict | None:
    sur = _surname(item["author"])
    candidates = [rec for rec in index if _surname(rec["author"]) == sur or _similar(item["author"], rec["author"]) > 0.72]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        candidates = index
    title_words = [w for w in _norm(item["title"]).split() if len(w) > 4]
    if title_words:
        by_title = [rec for rec in candidates if any(w in _norm(rec["text"]) for w in title_words)]
        if len(by_title) == 1:
            return by_title[0]
        if by_title:
            candidates = by_title
    best = None
    best_score = 0.0
    hint_key = _norm((hint or "")[:120])
    for rec in candidates:
        sa = _similar(item["author"], rec["author"])
        st = _similar(item["title"], rec["title"])
        score = sa * 0.35 + st * 0.45
        if hint_key and len(hint_key) > 20:
            score += _similar(hint_key, _norm(rec["text"][:160])) * 0.35
        if title_words:
            score += sum(1 for w in title_words if w in _norm(rec["text"])) * 0.08
        if score > best_score:
            best_score = score
            best = rec
    return best if best_score >= 0.45 else None


def _pdf_page_map() -> dict[int, int]:
    """Печатная страница → индекс PDF (0-based)."""
    mapping: dict[int, int] = {}
    if not POEMS_PDF.is_file():
        return mapping
    doc = fitz.open(POEMS_PDF)
    for i in range(doc.page_count):
        for m in re.finditer(r"(?:^|\n)\s*(\d{1,3})\s*(?:\n|$)", doc[i].get_text()):
            p = int(m.group(1))
            if 4 <= p <= 127 and p not in mapping:
                mapping[p] = i
    return mapping


def extract_from_pdf(item: dict, page_map: dict[int, int], *, validate: bool = True) -> str | None:
    start = item["page"]
    end = item["page_end"]
    if not POEMS_PDF.is_file():
        return None
    doc = fitz.open(POEMS_PDF)
    indices = []
    for p in range(start, end + 1):
        if p in page_map:
            indices.append(page_map[p])
    if not indices:
        return None
    parts = []
    for i in sorted(set(indices)):
        parts.append(doc[i].get_text())
    raw = _clean_poem_text("\n".join(parts))
    lines = []
    skip_headers = True
    for line in raw.splitlines():
        ln = line.strip()
        if not ln:
            if lines and lines[-1]:
                lines.append("")
            continue
        if _PAGE_NUM_RE.match(ln):
            continue
        if skip_headers:
            if re.fullmatch(r"(?:[А-ЯЁ]\s+){3,}", ln) or len(ln) < 4:
                continue
            if re.match(r"^[А-ЯЁ][а-яё]+ [А-ЯЁ]", ln) and len(ln) < 40:
                continue
            if ln.isupper() and len(ln) < 50:
                continue
            skip_headers = False
        lines.append(ln)
    text = _fix_ocr_starts("\n".join(lines).strip())
    # обрезать хвост следующего произведения (заголовок КАПСОМ)
    cut = []
    for line in text.splitlines():
        if cut and line.isupper() and 5 < len(line) < 60 and "ЛЕНИН" not in line:
            break
        cut.append(line)
    text = "\n".join(cut).strip()
    if not validate:
        return text if len(text) >= 40 else None
    return text if _readable(text, trusted=False) else None


def _chunk_poem(text: str, item: dict) -> list[str]:
    text = text.strip()
    if len(text) <= MAX_QUOTE:
        return [text]
    # длинные — по строфам
    stanzas = [s.strip() for s in re.split(r"\n\s*\n", text) if s.strip()]
    if not stanzas:
        stanzas = [ln for ln in text.splitlines() if ln.strip()]
    chunks: list[str] = []
    buf = ""
    for st in stanzas:
        candidate = (buf + "\n\n" + st).strip() if buf else st
        if len(candidate) <= MAX_QUOTE:
            buf = candidate
        else:
            if buf and len(buf) >= MIN_QUOTE:
                chunks.append(buf)
            buf = st if len(st) <= MAX_QUOTE else st[:MAX_QUOTE].rsplit("\n", 1)[0]
    if buf and len(buf) >= MIN_QUOTE:
        chunks.append(buf)
    return chunks or [text[:MAX_QUOTE]]


def _make_id(num: int, part: int, author: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", _norm(f"{author} {title}")[:36]).strip("_")
    return f"poem_{num:03d}_{part:02d}_{slug or 'item'}"


def build_entries() -> tuple[list[dict], list[dict]]:
    page_map = _pdf_page_map()
    ranges = {x["num"]: x for x in page_ranges()}
    print("Загрузка leninism.su…", file=sys.stderr)
    leninism = fetch_leninism_index()
    print(f"  leninism: {len(leninism)} стихов", file=sys.stderr)

    entries: list[dict] = []
    report: list[dict] = []

    for item in CATALOG:
        num = item["num"]
        rec = {**item, **ranges[num]}
        text = None
        src = None
        url = None

        pdf_hint = extract_from_pdf(rec, page_map, validate=False)

        for ext in EXTERNAL_URLS:
            if ext["num"] == num:
                fetched = _fetch_url(ext["url"])
                if fetched and _readable(fetched, trusted=True):
                    text, src, url = fetched, ext["url"].split("/")[2], ext["url"]
                    break

        if not text:
            hit = _match_leninism(rec, leninism, hint=pdf_hint)
            if hit and _readable(hit["text"], trusted=True):
                text, src, url = hit["text"], hit["source"], hit["url"]

        if not text and pdf_hint and _readable(pdf_hint, trusted=False):
            text, src = pdf_hint, "pdf_cleanup"

        status = "ok" if text and _readable(text, trusted=src != "pdf_cleanup") else "missing"
        report.append(
            {
                "num": num,
                "author": rec["author"],
                "title": rec["title"],
                "status": status,
                "source": src,
                "url": url,
                "chars": len(text) if text else 0,
            }
        )

        trusted = src != "pdf_cleanup"
        if not text or not _readable(text, trusted=trusted):
            print(f"SKIP #{num} {rec['author']} — {rec['title']}", file=sys.stderr)
            continue

        work = WORK
        if rec.get("note"):
            work = f"{WORK}, {rec['note']}"

        for part_i, chunk in enumerate(_chunk_poem(text, rec), start=1):
            entries.append(
                {
                    "id": _make_id(num, part_i, rec["author"], rec["title"]),
                    "catalog_num": num,
                    "part": part_i,
                    "author": rec["author"],
                    "work": work,
                    "title": rec["title"],
                    "quote": chunk,
                    "tag": "стихи",
                    "source": src,
                    "source_url": url,
                }
            )
        print(f"OK #{num} {rec['author']} — {rec['title']} ({src}, {len(text)} зн.)", file=sys.stderr)

    return entries, report


def main() -> None:
    entries, report = build_entries()
    ok = sum(1 for r in report if r["status"] == "ok")
    data = {
        "_comment": "Стихи о Ленине — чистые тексты для «Сказка на ночь». Пересборка: tools/build_lenin_poems.py",
        "work": WORK,
        "entries": entries,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(entries)} фрагментов из {ok}/{len(CATALOG)} стихотворений → {OUT}")


if __name__ == "__main__":
    main()
