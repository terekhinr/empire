#!/usr/bin/env python3
"""Данилкин «Пантократор» (EPUB) → цитаты для рубрик канала Ленин + подбор фото Commons."""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EPUB = ROOT / "data" / "lenin" / "Пантократор.epub"
OUT = ROOT / "data" / "lenin_danilkin_candidates.json"
RUBRICS = ROOT / "data" / "lenin_rubrics.json"

SOURCE = "Л. Данилкин, «Ленин: Пантократор солнечных пылинок» (2017)"
MIN_LEN = 260
MAX_LEN = 720
TARGET_COUNT = 75
MAX_PER_CHAPTER = 4

_SENT_END = re.compile(r'[.!?…»]["»\s]*$')

# Глава / ключевые слова → файл на Wikimedia Commons (как в lenin_rubrics.json).
IMAGE_BY_TOPIC: list[tuple[str, str, str]] = [
    (r"париж|лонжюмо|франц|мюнхен|лейпциг|искр", "Vladimir Lenin after finishing his exile in Siberia, 1900-1.jpg", "portrait"),
    (r"финляндск|вокзал|пломбир|вагон|апрел", "The eve of October (speech VI Lenin at the Finland station).jpg", "portrait"),
    (r"симбирск|ульяновск|детств|1870", "Vladimir Lenin, 1917.jpg", "portrait"),
    (r"сибир|шушенск|ссылк", "Vladimir Lenin after finishing his exile in Siberia, 1900-1.jpg", "portrait"),
    (r"капри|махизм|богданов|эмпириокрит", "Vladimir Lenin, 1917.jpg", "portrait"),
    (r"кремл|горьк[иы]\s*192|покушен|террор|смольн", "Vladimir Lenin, 1917.jpg", "portrait"),
    (r"1905|ваза|революц", "Lenin-poster.jpg", "poster"),
    (r"съезд|лондон|брунсвик|швейцар|женев", "Vladimir Lenin after finishing his exile in Siberia, 1900-1.jpg", "portrait"),
    (r"кино|ромм|фильм", "Lenin in October movie, 1937 final.jpg", "film_still"),
    (r"литератур|роман|писател", "Vladimir Lenin, 1917.jpg", "portrait"),
]

_SKIP_RE = re.compile(
    r"ISBN|УДК|ББК|знак информационной|рекомендуемой.{0,20}литератур|"
    r"список «Ленин-100»|жилые комплексы|музей.{0,30}доживает",
    re.I,
)


def _extract_paragraphs(epub: Path) -> list[tuple[str, str]]:
    with zipfile.ZipFile(epub) as z:
        container = ET.fromstring(z.read("META-INF/container.xml"))
        ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
        opf_path = container.find(".//c:rootfile", ns).attrib["full-path"]
        opf = ET.fromstring(z.read(opf_path))
        opf_ns = {"x": "http://www.idpf.org/2007/opf"}
        manifest = {
            item.attrib["id"]: item.attrib["href"]
            for item in opf.findall(".//x:manifest/x:item", opf_ns)
        }
        base = str(Path(opf_path).parent)
        chapter = ""
        paras: list[tuple[str, str]] = []
        for item in opf.findall(".//x:spine/x:itemref", opf_ns):
            href = manifest[item.attrib["idref"]]
            path = f"{base}/{href}" if base != "." else href
            path = path.replace("\\", "/")
            try:
                root = ET.fromstring(z.read(path))
            except ET.ParseError:
                continue
            for el in root.iter():
                tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
                if tag in ("h1", "h2", "h3", "title"):
                    t = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
                    if t and len(t) < 120 and not t.isdigit():
                        chapter = t
                elif tag == "p":
                    t = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
                    if len(t) >= 80:
                        paras.append((chapter, t))
    return paras


def _quote_chunks(text: str) -> list[str]:
    """Один абзац → одна или несколько цельных цитат."""
    one = _trim_sentences(text)
    if one:
        return [one]
    sents = re.split(r"(?<=[.!?…»])\s+", text.strip())
    if len(sents) < 2:
        return []
    chunks: list[str] = []
    buf = ""
    for sent in sents:
        sent = sent.strip()
        if not sent:
            continue
        candidate = f"{buf} {sent}".strip() if buf else sent
        if len(candidate) <= MAX_LEN:
            buf = candidate
            continue
        if buf:
            ok = _trim_sentences(buf)
            if ok:
                chunks.append(ok)
        buf = sent
    if buf:
        ok = _trim_sentences(buf)
        if ok:
            chunks.append(ok)
    return chunks


def _trim_sentences(text: str, *, max_len: int = MAX_LEN) -> str | None:
    t = text.strip()
    if len(t) > max_len:
        chunk = t[: max_len + 1]
        m = list(re.finditer(r"[.!?…](?:\s+|$)", chunk))
        if not m:
            return None
        t = t[: m[-1].end()].strip()
    if not _SENT_END.search(t):
        return None
    if t.endswith("-") or re.search(r"\w-\s*$", t):
        return None
    if len(t) < MIN_LEN:
        return None
    return t


def _score(chapter: str, text: str) -> float:
    if _SKIP_RE.search(text) or _SKIP_RE.search(chapter):
        return -1.0
    if not re.search(r"ленин|ильич|ульянов", text, re.I):
        return -1.0
    if not _trim_sentences(text) and not _quote_chunks(text):
        return -1.0
    text = _trim_sentences(text) or _quote_chunks(text)[0]
    n = len(text)
    score = 0.0
    mid = (MIN_LEN + MAX_LEN) / 2
    score += 3.0 - abs(n - mid) / 180.0
    if "«" in text and "»" in text:
        score += 2.5
    if text.count("—") >= 1:
        score += 0.8
    if re.search(r"ленин", text, re.I):
        score += 1.5
    if re.search(r"революц|париж|кремл|вагон|съезд|капри|горьк", text, re.I):
        score += 1.0
    if re.search(r"автор этой биограф|книга могла бы|читатель", text, re.I):
        score -= 1.5
    return score


def _pick_image(chapter: str, text: str) -> tuple[str, str]:
    blob = f"{chapter} {text}".lower()
    for pat, fname, kind in IMAGE_BY_TOPIC:
        if re.search(pat, blob, re.I):
            return fname, kind
    return "Vladimir Lenin, 1917.jpg", "portrait"


def _commentary(chapter: str, text: str) -> str:
    ch = chapter.strip() or "биография"
    if re.search(r"париж", ch, re.I):
        return f"Фрагмент о {ch}: у Данилкина эмиграция — не открытка, а работа текста, споров и политической подготовки."
    if re.search(r"вагон|финляндск|апрел", ch, re.I):
        return "Данилкин разбирает апрель 1917-го без шпионского романа: ставка на скорость политического возвращения."
    if re.search(r"кремл|террор|покушен", ch, re.I):
        return "О московском периоде: Данилкин не снимает с Ленина ответственность, но и не сводит её к «психике вождя»."
    if re.search(r"капри|мах", ch, re.I):
        return "Каприйские эпизоды — спор о философии и политике, где Ленин остаётся жёстким редактором собственной линии."
    if re.search(r"1905|меньшевик", ch, re.I):
        return "О расколе и интеллигенции: у Данилкина это не абстрактная ссора, а долгая история ленинского отношения к «своим» и «чужим»."
    return f"Цитата из главы «{ch}»: биография как спор с легендой, а не парадный монолог."


def _format_quote(text: str) -> str:
    t = text.strip()
    if not (t.startswith("«") or t.startswith('"')):
        t = f"«{t}»"
    return t


def _slug(chapter: str, seq: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", chapter.lower()[:28]).strip("_") or "frag"
    return f"danilkin_{s}_{seq:03d}"


def _existing_quotes(data: dict) -> set[str]:
    out: set[str] = set()
    for block in (data.get("rubrics") or {}).values():
        for e in block.get("entries", []):
            if "данилкин" in (e.get("source") or "").lower() or e.get("tag") == "данилкин":
                q = (e.get("quote") or e.get("text") or "")[:120]
                out.add(q)
    return out


def _rubric_for(chapter: str, text: str) -> str:
    if re.search(r"литератур|роман|писател|поэт|книг", f"{chapter} {text}", re.I):
        return "literature"
    if re.search(r"кино|фильм|ромм", f"{chapter} {text}", re.I):
        return "cinema"
    return "biography"


def build_candidates() -> list[dict]:
    if not EPUB.is_file():
        raise SystemExit(f"Нет EPUB: {EPUB}")
    paras = _extract_paragraphs(EPUB)
    scored: list[tuple[float, str, str]] = []
    for ch, p in paras:
        for chunk in _quote_chunks(p) or []:
            s = _score(ch, chunk)
            if s > 0:
                scored.append((s, ch, chunk))
    scored.sort(key=lambda x: (-x[0], x[1], x[2][:40]))

    seen_prefix: set[str] = set()
    per_chapter: dict[str, int] = {}
    entries: list[dict] = []
    seq = 0
    for s, ch, p in scored:
        pref = p[:90]
        if pref in seen_prefix:
            continue
        ch_key = ch.strip().lower()[:40]
        if per_chapter.get(ch_key, 0) >= MAX_PER_CHAPTER:
            continue
        seen_prefix.add(pref)
        per_chapter[ch_key] = per_chapter.get(ch_key, 0) + 1
        seq += 1
        img, kind = _pick_image(ch, p)
        ch_clean = ch.strip() or "фрагмент"
        src = f"{SOURCE}, гл. «{ch_clean}»"
        entry = {
            "id": _slug(ch_clean, seq),
            "source": src,
            "verbatim": True,
            "commentary": _commentary(ch_clean, p),
            "tag": "данилкин",
            "image_file": img,
            "image_kind": kind,
            "quote": _format_quote(p),
            "chapter": ch_clean,
            "rubric": _rubric_for(ch_clean, p),
            "_score": round(s, 2),
        }
        entries.append(entry)
        if len(entries) >= TARGET_COUNT:
            break
    return entries


def _strip_old_danilkin_auto(data: dict) -> None:
    """Удалить автосгенерированные danilkin_* (оставить lit_/bio_ ручные)."""
    for block in (data.get("rubrics") or {}).values():
        block["entries"] = [
            e
            for e in block.get("entries", [])
            if not (e.get("id") or "").startswith("danilkin_")
        ]


def merge_into_rubrics(entries: list[dict], *, dry_run: bool = False, replace_auto: bool = False) -> int:
    data = json.loads(RUBRICS.read_text(encoding="utf-8"))
    if replace_auto:
        _strip_old_danilkin_auto(data)
    existing_ids = {
        e.get("id")
        for block in (data.get("rubrics") or {}).values()
        for e in block.get("entries", [])
    }
    existing_q = _existing_quotes(data)
    added = 0
    for entry in entries:
        if entry["quote"][:100] in existing_q:
            continue
        eid = entry["id"]
        base = eid
        n = 2
        while eid in existing_ids:
            eid = f"{base}_{n}"
            n += 1
        row = {k: v for k, v in entry.items() if not k.startswith("_") and k != "chapter" and k != "rubric"}
        row["id"] = eid
        rubric = entry["rubric"]
        data["rubrics"][rubric]["entries"].append(row)
        existing_ids.add(eid)
        existing_q.add(entry["quote"][:100])
        added += 1
    if not dry_run and added:
        RUBRICS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return added


def main() -> None:
    entries = build_candidates()
    OUT.write_text(json.dumps({"entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    dry = "--dry-run" in sys.argv
    replace = "--replace" in sys.argv or not dry
    added = merge_into_rubrics(entries, dry_run=dry, replace_auto=replace)
    print(f"Кандидаты: {len(entries)} → {OUT}")
    print(f"{'Было бы добавлено' if dry else 'Добавлено'} в {RUBRICS.name}: {added}")
    print(f"  Всего в пуле: {len(entries)}")
    for e in entries[:5]:
        print(f"  • [{e['rubric']}] {e['id']} ({len(e['quote'])} зн.) — {e['chapter'][:40]}")


if __name__ == "__main__":
    main()
