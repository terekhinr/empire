#!/usr/bin/env python3
"""Собирает data/stern_curated.json из markdown (Gemini ingest)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.parse_gdepar_duo_import import POST_BLOCK_RE, _parse_frontmatter  # noqa: E402

SRC = ROOT / "docs/content_factory/gemini_export/generated/stern_all_ingested.md"
OUT = ROOT / "data/stern_curated.json"


def _md_to_html(body: str) -> str:
    lines = []
    for line in body.strip().splitlines():
        s = line.strip()
        if not s:
            lines.append("")
            continue
        if s.startswith("#") and not s.startswith("<"):
            continue
        lines.append(s)
    return "\n".join(lines).strip()


def parse_entries(text: str) -> list[dict]:
    by_id: dict[str, dict] = {}
    start = text.find("---\n")
    blob = text[start:] if start >= 0 else text
    for fm_raw, body in POST_BLOCK_RE.findall(blob):
        meta = _parse_frontmatter(fm_raw)
        eid = meta.get("id")
        if not eid or not eid.startswith("stern_"):
            continue
        slot = meta.get("slot") or ("0930" if "_0930_" in eid else "1900")
        by_id[eid] = {
            "id": eid,
            "slot": slot,
            "topic_raw": meta.get("topic_raw", ""),
            "body_html": _md_to_html(body),
            "hashtags": meta.get("hashtags", ""),
            "image_prompt_en": meta.get("image_prompt_en"),
        }
    return list(by_id.values())


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"Нет файла {SRC} — сначала ingest Gemini")
    text = SRC.read_text(encoding="utf-8")
    entries = parse_entries(text)
    if not entries:
        raise SystemExit("0 постов Stern — проверь формат")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_comment": "Курированные Stern без LLM. Импорт: parse_stern_curated_import.py",
        "entries": entries,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    n0930 = sum(1 for e in entries if e.get("slot") == "0930")
    n1900 = sum(1 for e in entries if e.get("slot") == "1900")
    print(f"OK {len(entries)} imported ({n0930}×0930, {n1900}×1900) → {OUT}")


if __name__ == "__main__":
    main()
