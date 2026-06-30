#!/usr/bin/env python3
"""Собирает data/gdepar_duo_curated.json из markdown-батча."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "gdepar_duo_curated_import_raw.md"
OUT = ROOT / "data" / "gdepar_duo_curated.json"

FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Gemini: между постами «---\nid:» без пустой строки
POST_BLOCK_RE = re.compile(
    r"---\s*\n(.*?)\n---\s*\n(.*?)(?=\n---\s*\nid:|\Z)",
    re.DOTALL,
)
FIELD_RE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)


def _parse_frontmatter(block: str) -> dict:
    meta: dict = {}
    for m in FIELD_RE.finditer(block):
        key, val = m.group(1), m.group(2).strip()
        if val == "null":
            meta[key] = None
        else:
            meta[key] = val.strip('"')
    return meta


def _md_to_html(body: str) -> str:
    lines_out: list[str] = []
    for line in body.strip().splitlines():
        s = line.strip()
        if not s:
            lines_out.append("")
            continue
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        if s.startswith("<b>") and s.endswith("</b>") and ":" not in s:
            lines_out.append(f"🔥 {s}")
        else:
            lines_out.append(s)
    return "\n".join(lines_out).strip()


def parse_posts(text: str) -> list[dict]:
    posts: list[dict] = []
    # пропустить markdown-шапку
    start = text.find("\n---\n")
    if start == -1 and text.strip().startswith("---"):
        blob = text
    elif start >= 0:
        blob = text[start + 1 :]
    else:
        blob = text
    for fm_raw, body in POST_BLOCK_RE.findall(blob):
        meta = _parse_frontmatter(fm_raw)
        eid = meta.get("id")
        if not eid:
            continue
        entry = {
            "id": eid,
            "pool": meta.get("pool", "practice"),
            "tag": meta.get("tag", "гдепар"),
            "headline": meta.get("headline", eid),
            "body_html": _md_to_html(body),
            "image_file": meta.get("image_file"),
        }
        if meta.get("hashtags"):
            entry["hashtags"] = meta["hashtags"]
        posts.append(entry)
    return posts


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"Создайте {SRC} — см. docs/gdepar_duo_curated.md")
    posts = parse_posts(SRC.read_text(encoding="utf-8"))
    if not posts:
        raise SystemExit("Нет постов в markdown")
    existing = {}
    if OUT.is_file():
        try:
            existing = json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    by_id = {e["id"]: e for e in existing.get("entries") or []}
    for p in posts:
        by_id[p["id"]] = p
    out = {
        "_comment": existing.get("_comment") or "Ручные посты Михалыч↔Кириллыч",
        "_pools": existing.get("_pools") or {},
        "entries": list(by_id.values()),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(posts)} imported → {len(out['entries'])} total in {OUT}")


if __name__ == "__main__":
    main()
