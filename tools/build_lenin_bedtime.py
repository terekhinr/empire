#!/usr/bin/env python3
"""Перескан сказок/рассказов/стихов о Ленине → lenin_bedtime_stories.json + RAG input."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "lenin_bedtime_stories.json"
POEMS_CURATED = ROOT / "data" / "lenin_poems_curated.json"
HISTORY = ROOT / "data" / "lenin_bedtime_used.json"
RAG_BOOKS = ROOT / "kb_sources" / "lenin" / "books"
DATA_LENIN = ROOT / "data" / "lenin"

SOURCES = [
    {
        "path": ROOT / "Замостьянов А.А. (сост.) - Сказки о Ленине (Родительское собрание) - 2023.pdf",
        "work": "Замостьянов А.А. (сост.), «Сказки о Ленине» (2023)",
        "author": "Замостьянов А.А.",
        "tag": "сказка",
        "kind": "сказки",
    },
    {
        "path": ROOT / "Кононов А.Т. - Рассказы о Ленине - 1974.pdf",
        "work": "А.Т. Кононов, «Рассказы о Ленине» (1974)",
        "author": "А.Т. Кононов",
        "tag": "рассказ",
        "kind": "рассказы",
    },
    {
        "path": DATA_LENIN / "Кононов А.Т. - Рассказы о Ленине - 1974.pdf",
        "work": "А.Т. Кононов, «Рассказы о Ленине» (1974)",
        "author": "А.Т. Кононов",
        "tag": "рассказ",
        "kind": "рассказы",
    },
]

POEMS = DATA_LENIN / "Стихи о Ленине (Школьная библиотека) — 1974.pdf"

_JUNK_RE = re.compile(
    r"[\u0400-\u04FF]{0,2}[^\u0400-\u04FF\u0020-\u007E«»—–\.\,\!\?\:\;\-\(\)\"\'\n]{3,}"
)


def _clean(text: str) -> str:
    t = text.replace("\u00ad", "").replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _readable(text: str, *, min_len: int = 180, require_lenin: bool = True) -> bool:
    if len(text) < min_len:
        return False
    if require_lenin and "Ленин" not in text and "Ильич" not in text and "Ульянов" not in text:
        return False
    cyr = len(re.findall(r"[а-яА-ЯёЁ]", text))
    if cyr < len(text) * 0.55:
        return False
    if _JUNK_RE.search(text):
        return False
    if text.count("ǁ") + text.count("Ƽ") > 2:
        return False
    return True


def _extract_pdf(path: Path) -> str:
    doc = fitz.open(path)
    parts = []
    for page in doc:
        parts.append(page.get_text())
    return _clean("\n".join(parts))


def _chunk_stories(text: str, *, min_len: int = 250, max_len: int = 1400) -> list[str]:
    """Режем по абзацам и диалогам."""
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(p) < 40:
            continue
        if len(buf) + len(p) < max_len:
            buf = (buf + "\n\n" + p).strip() if buf else p
        else:
            if buf and _readable(buf):
                chunks.append(buf)
            buf = p
    if buf and _readable(buf):
        chunks.append(buf)
    # склейка коротких хвостов
    merged: list[str] = []
    for c in chunks:
        if merged and len(merged[-1]) < min_len:
            merged[-1] = merged[-1] + "\n\n" + c
        else:
            merged.append(c)
    return [c[:max_len] for c in merged if _readable(c)]


def _make_id(kind: str, idx: int, preview: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", preview[:40].lower())[:24].strip("_")
    return f"{kind}_{idx:03d}_{slug or 'item'}"


def build_entries() -> list[dict]:
    seen_text: set[str] = set()
    entries: list[dict] = []
    idx = 0

    for src in SOURCES:
        path = src["path"]
        if not path.is_file():
            print(f"SKIP missing: {path}", file=sys.stderr)
            continue
        print(f"Scan: {path.name}")
        text = _extract_pdf(path)
        for chunk in _chunk_stories(text):
            key = chunk[:200]
            if key in seen_text:
                continue
            seen_text.add(key)
            idx += 1
            quote = chunk if chunk.startswith("«") else f"«{chunk}»"
            entries.append(
                {
                    "id": _make_id(src["kind"], idx, chunk),
                    "work": src["work"],
                    "author": src["author"],
                    "quote": quote,
                    "tag": src["tag"],
                }
            )

    if POEMS_CURATED.is_file():
        print(f"Load: {POEMS_CURATED.name}")
        curated = json.loads(POEMS_CURATED.read_text(encoding="utf-8"))
        for e in curated.get("entries", []):
            quote = (e.get("quote") or "").strip()
            if not quote or not _readable(quote, min_len=80, require_lenin=False):
                continue
            key = quote[:200]
            if key in seen_text:
                continue
            seen_text.add(key)
            idx += 1
            entries.append(
                {
                    "id": e.get("id") or _make_id("стихи", idx, quote),
                    "work": e.get("work") or "«Стихи о Ленине» (Школьная библиотека, 1974)",
                    "author": e.get("author") or "сборник",
                    "title": e.get("title", ""),
                    "quote": quote,
                    "tag": "стихи",
                }
            )
    elif POEMS.is_file():
        print(f"WARN: нет {POEMS_CURATED.name}, fallback OCR PDF", file=sys.stderr)
        print(f"Scan: {POEMS.name}")
        text = _extract_pdf(POEMS)
        for chunk in _chunk_stories(text, min_len=120, max_len=900):
            key = chunk[:200]
            if key in seen_text:
                continue
            seen_text.add(key)
            idx += 1
            entries.append(
                {
                    "id": _make_id("стихи", idx, chunk),
                    "work": "«Стихи о Ленине» (Школьная библиотека, 1974)",
                    "author": "сборник",
                    "quote": chunk,
                    "tag": "стихи",
                }
            )

    return entries


def sync_rag_books() -> None:
    RAG_BOOKS.mkdir(parents=True, exist_ok=True)
    for src in SOURCES:
        p = src["path"]
        if p.is_file():
            dest = RAG_BOOKS / p.name
            if not dest.exists():
                shutil.copy2(p, dest)
                print(f"RAG copy: {dest.name}")
    if POEMS.is_file():
        dest = RAG_BOOKS / POEMS.name
        if not dest.exists():
            shutil.copy2(POEMS, dest)
            print(f"RAG copy: {dest.name}")


def main() -> None:
    entries = build_entries()
    data = {
        "_comment": "Сказка на ночь: цитаты из ленинианы. Пересборка: tools/build_lenin_bedtime.py",
        "entries": entries,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if not HISTORY.is_file():
        HISTORY.write_text('{"by_rubric": {"_all": []}}', encoding="utf-8")
    sync_rag_books()
    print(f"OK: {len(entries)} entries → {OUT}")


if __name__ == "__main__":
    main()
