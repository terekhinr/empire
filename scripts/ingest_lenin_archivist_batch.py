#!/usr/bin/env python3
"""Ingest Archivist NL posts → lenin_rubrics + bedtime.

Supports markdown with blocks:

  #### N. РЕЖИМ: cinema
  ...
  ---

  or ### РЕЖИМ: monument / bedtime

Usage:
  ./venv/bin/python scripts/ingest_lenin_archivist_batch.py PATH.md
  ./venv/bin/python scripts/ingest_lenin_archivist_batch.py PATH.md --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUBRICS = ROOT / "data" / "lenin_rubrics.json"
BEDTIME = ROOT / "data" / "lenin_bedtime_stories.json"

MODE_TO_RUBRIC = {
    "cinema": "cinema",
    "monument": "art",
    "bedtime": "bedtime",
}

# cinema-looking but really literature / art
FORCE_RUBRIC = [
    (re.compile(r"пастернак|живаго|рахметов|чернышевск|маяковск|гимн новейшего|vade mecum|белый волк|солдатский хлеб|легенда о фонарях|наш герб|разговор о тепле|баллада о портрете|первая годовщина|сандалов|кабинете космонавта|лешего|горького", re.I), "literature"),
    (re.compile(r"снимок|наппельбаум|оцуп|булл|бродск|плакат|альтман|геоглиф|письмо тотем|гора самоцвет|газеты без бумаги", re.I), "art"),
]

IMAGE_HINTS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"октябре|ромм|щукин", re.I), "Lenin in October movie, 1937 final.jpg", "film_still"),
    (re.compile(r"1918 год", re.I), "Lenin in October movie, 1937 final.jpg", "film_still"),
    (re.compile(r"одной планете|смоктунов", re.I), "October film Lenin.jpg", "film_still"),
    (re.compile(r"побег|абдулов", re.I), "Vladimir Lenin giving a speech.jpg", "film_still"),
    (re.compile(r"бродск|смольн", re.I), "Brodskiy Isaac-Vladimir Lenin in Smolny.jpg", "painting"),
    (re.compile(r"плакат", re.I), "Lenin-poster.jpg", "poster"),
    (re.compile(r"волгоград|вучетич", re.I), "Monument to Lenin on Lenin Square in Volgograd.jpg", "monument"),
    (re.compile(r"памятник|монумент|стела|шалаш|мемориал", re.I), "Monument to Lenin on Lenin Square in Volgograd.jpg", "monument"),
    (re.compile(r".", re.I), "Vladimir Lenin, 1917.jpg", "portrait"),
]

LABEL_RE = re.compile(
    r"^(О чём|Как представлен Ленин|1–2 факта|1-2 факта|Архивариус|Опора|Фото|Где стоит|Когда открыт|Когда создан|Когда открыт / автор)\s*:\s*",
    re.I,
)
OPORA_LINE = re.compile(r"^Опора\s*:.*$", re.I | re.M)
FOTO_LINE = re.compile(r"^Фото\s*:.*$", re.I | re.M)
MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
HASHTAG_LINE = re.compile(r"^#\S.*$", re.M)
MODE_SPLIT = re.compile(
    r"(?:^|\n)(?:#{1,4}\s*(?:Пост\s*№\s*\d+\.\s*)?)?РЕЖИМ\s*:\s*(cinema|monument|bedtime)\s*\n",
    re.I,
)
EMOJI_TITLE = re.compile(
    r"^(🎬|🗿|🌙)\s*\*?\*?(.+?)\*?\*?\s*$",
    re.M,
)


def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[«»\"'`]", "", s)
    s = re.sub(r"[^a-zа-яё0-9]+", "_", s, flags=re.I)
    return s.strip("_")[:48] or "x"


def norm_key(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"[^\wа-яё]+", " ", s.lower(), flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, norm_key(a), norm_key(b)).ratio()


def clean_body(raw: str) -> tuple[str, str]:
    """Return (body_without_source, source_line)."""
    text = raw.strip()
    text = MD_BOLD.sub(r"\1", text)
    source = ""
    m_op = OPORA_LINE.search(text)
    if m_op:
        source = re.sub(r"^Опора\s*:\s*", "", m_op.group(0), flags=re.I).strip()
        text = OPORA_LINE.sub("", text)
    text = FOTO_LINE.sub("", text)
    text = HASHTAG_LINE.sub("", text)
    # drop instructional photo placeholders
    text = re.sub(r"Укажите описание.*", "", text, flags=re.I)
    m = re.search(r"(?:\*Источник:\s*(.+?)\*|Источник:\s*(.+))", text, re.I)
    if m:
        src2 = (m.group(1) or m.group(2) or "").strip().rstrip(".")
        if not source:
            source = src2
        text = text[: m.start()] + text[m.end() :]
    # strip leading emoji title line — stored separately
    text = re.sub(r"^(🎬|🗿|🌙)\s*.+\n+", "", text.strip())
    lines = [ln.strip() for ln in text.splitlines()]
    body = "\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    body = body.replace("*", "")
    return body, source


def extract_title(block: str) -> str:
    m = EMOJI_TITLE.search(block)
    if m:
        return m.group(2).strip().strip("*").strip()
    for ln in block.splitlines():
        ln = ln.strip()
        if ln and not ln.upper().startswith("РЕЖИМ") and not ln.startswith("#"):
            return MD_BOLD.sub(r"\1", ln)[:120]
    return "без названия"


def pick_image(title: str, body: str) -> tuple[str, str]:
    blob = f"{title}\n{body}"
    for rx, fname, kind in IMAGE_HINTS:
        if rx.search(blob):
            return fname, kind
    return "Vladimir Lenin, 1917.jpg", "portrait"


def resolve_rubric(mode: str, title: str, body: str) -> str:
    if mode == "bedtime":
        return "bedtime"
    if mode == "monument":
        return "art"
    blob = f"{title}\n{body}"
    for rx, key in FORCE_RUBRIC:
        if rx.search(blob):
            return key
    # poetry bedtime mislabeled as cinema in some batches
    if re.search(r"стих|поэм", title, re.I) and "фильм" not in body.lower():
        return "literature"
    return MODE_TO_RUBRIC.get(mode, "cinema")


def parse_blocks(text: str) -> list[dict]:
    # Normalize: ensure РЕЖИМ markers are findable
    text = text.replace("\r\n", "\n")
    parts = MODE_SPLIT.split(text)
    # parts: [preamble, mode1, body1, mode2, body2, ...]
    out: list[dict] = []
    if len(parts) < 3:
        return out
    for i in range(1, len(parts), 2):
        mode = parts[i].lower().strip()
        body_raw = parts[i + 1] if i + 1 < len(parts) else ""
        # cut at next --- horizontal rule that starts a new section header-ish
        body_raw = re.split(r"\n---+\n(?=\s*(?:#{1,4}|РЕЖИМ))", body_raw, maxsplit=1)[0]
        title = extract_title(body_raw)
        body, source = clean_body(body_raw)
        if len(norm_key(body)) < 80:
            continue
        rubric = resolve_rubric(mode, title, body)
        out.append(
            {
                "mode": mode,
                "rubric": rubric,
                "title": title,
                "body": body,
                "source": source,
            }
        )
    return out


def dedupe_parsed(posts: list[dict]) -> list[dict]:
    kept: list[dict] = []
    for p in posts:
        key = norm_key(p["title"] + " " + p["body"][:200])
        dup = False
        for k in kept:
            if similar(key, norm_key(k["title"] + " " + k["body"][:200])) >= 0.86:
                # keep longer body
                if len(p["body"]) > len(k["body"]):
                    k.update(p)
                dup = True
                break
        if not dup:
            kept.append(p)
    return kept


def overlaps_existing(body: str, title: str, existing_blobs: list[str]) -> bool:
    probe = norm_key(title + " " + body[:240])
    for b in existing_blobs:
        if similar(probe, b) >= 0.82:
            return True
    return False


def to_rubric_entry(p: dict) -> dict:
    title = p["title"]
    body = p["body"]
    src = p["source"] or title
    # Prefer explicit work title in source
    if p["mode"] == "monument" and "памятник" not in src.lower():
        src = f"{title} — {src}" if src != title else title
    img, kind = pick_image(title, body)
    tag = {
        "cinema": "кино",
        "art": "памятник" if p["mode"] == "monument" else "искусство",
        "literature": "литература",
    }.get(p["rubric"], "ленин")
    if re.search(r"сним|фото|наппель|оцуп|булл", title + body, re.I):
        tag = "фото"
    hid = hashlib.md5(norm_key(title).encode()).hexdigest()[:8]
    eid = f"arch_{p['rubric'][:3]}_{slugify(title)}_{hid}"
    # quote = title + body for readable blockquote
    quote = f"{title}\n\n{body}".strip()
    # drop trailing Архивариус empty
    quote = re.sub(r"\nАрхивариус:\s*$", "", quote)
    return {
        "id": eid,
        "source": src[:200],
        "text": quote,
        "quote": quote,
        "note": "",
        "tag": tag,
        "image_file": img,
        "image_kind": kind,
        "archivist": True,
    }


def to_bedtime_entry(p: dict) -> dict:
    body = p["body"]
    # extract blockquote-ish narrative
    quote = body
    m = re.search(r"[«\"](.+)[»\"]", body, re.S)
    if m and len(m.group(0)) > 120:
        quote = m.group(0)
        if not quote.startswith("«"):
            quote = f"«{quote.strip('\"')}»"
    # strip Архивариус commentary from quote when long narrative present
    quote = re.split(r"\nАрхивариус:\s*", quote, maxsplit=1)[0].strip()
    src = p["source"] or p["title"]
    author, work = "", src
    if "," in src:
        author, work = [x.strip() for x in src.split(",", 1)]
    hid = hashlib.md5(norm_key(p["title"] + quote[:80]).encode()).hexdigest()[:8]
    tag = "стихи" if re.search(r"стих|поэм", p["title"] + src, re.I) else "сказка"
    return {
        "id": f"arch_bed_{slugify(p['title'])}_{hid}",
        "author": author or "лениниана",
        "work": work or p["title"],
        "quote": quote if quote.startswith("«") else f"«{quote}»",
        "tag": tag,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    text = args.batch.read_text(encoding="utf-8")
    posts = dedupe_parsed(parse_blocks(text))
    print(f"parsed unique blocks: {len(posts)}")

    rub = json.loads(RUBRICS.read_text(encoding="utf-8"))
    bed = json.loads(BEDTIME.read_text(encoding="utf-8"))

    existing_rub: list[str] = []
    for key, meta in (rub.get("rubrics") or {}).items():
        for e in meta.get("entries") or []:
            existing_rub.append(norm_key((e.get("source") or "") + " " + (e.get("quote") or e.get("text") or "")[:240]))
    existing_bed = [
        norm_key((e.get("work") or "") + " " + (e.get("quote") or "")[:240])
        for e in bed.get("entries") or []
    ]

    added = {"cinema": 0, "art": 0, "literature": 0, "bedtime": 0, "skip": 0}
    new_rub_entries: dict[str, list] = {"cinema": [], "art": [], "literature": []}
    new_bed: list = []

    for p in posts:
        if p["rubric"] == "bedtime":
            if overlaps_existing(p["body"], p["title"], existing_bed):
                added["skip"] += 1
                continue
            e = to_bedtime_entry(p)
            new_bed.append(e)
            existing_bed.append(norm_key(e["work"] + " " + e["quote"][:240]))
            added["bedtime"] += 1
            continue
        if overlaps_existing(p["body"], p["title"], existing_rub):
            added["skip"] += 1
            continue
        e = to_rubric_entry(p)
        key = p["rubric"] if p["rubric"] in new_rub_entries else "cinema"
        new_rub_entries[key].append(e)
        existing_rub.append(norm_key(e["source"] + " " + e["quote"][:240]))
        added[key] += 1

    print("add:", added)
    if args.dry_run:
        for k, lst in new_rub_entries.items():
            for e in lst[:3]:
                print(f"  [{k}] {e['id']}: {e['source'][:60]}")
        for e in new_bed[:3]:
            print(f"  [bed] {e['id']}: {e['work'][:50]}")
        return 0

    for key, lst in new_rub_entries.items():
        rub["rubrics"][key].setdefault("entries", []).extend(lst)
    bed.setdefault("entries", []).extend(new_bed)
    RUBRICS.write_text(json.dumps(rub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    BEDTIME.write_text(json.dumps(bed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "totals:",
        {k: len(rub["rubrics"][k]["entries"]) for k in ("cinema", "art", "literature", "biography")},
        "bedtime",
        len(bed["entries"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
