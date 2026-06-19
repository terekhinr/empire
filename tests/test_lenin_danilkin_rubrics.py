"""Цитаты Данилкина из EPUB — длина и целостность для TG."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUBRICS = ROOT / "data" / "lenin_rubrics.json"
CANDIDATES = ROOT / "data" / "lenin_danilkin_candidates.json"

_SENT_END = re.compile(r'[.!?…»]["»\s]*$')


def _danilkin_entries() -> list[dict]:
    data = json.loads(RUBRICS.read_text(encoding="utf-8"))
    out = []
    for block in (data.get("rubrics") or {}).values():
        for e in block.get("entries", []):
            if (e.get("id") or "").startswith("danilkin_"):
                out.append(e)
    return out


def test_danilkin_candidates_file_exists():
    assert CANDIDATES.is_file()
    entries = json.loads(CANDIDATES.read_text(encoding="utf-8"))["entries"]
    assert len(entries) >= 70


def test_danilkin_pool_size_in_rubrics():
    auto = _danilkin_entries()
    assert len(auto) >= 70


def test_danilkin_quotes_tg_length_and_complete():
    for e in _danilkin_entries():
        q = (e.get("quote") or "").strip()
        inner = q.strip("«»")
        assert 260 <= len(inner) <= 750, e["id"]
        assert _SENT_END.search(inner), e["id"]
        assert e.get("verbatim") and e.get("image_file")


def test_danilkin_images_on_disk():
    media = ROOT / "media" / "lenin" / "rubrics"
    missing = []
    for e in _danilkin_entries():
        p = media / f"{e['id']}.jpg"
        if not p.is_file() or p.stat().st_size < 2048:
            missing.append(e["id"])
    assert not missing, f"no image: {missing}"
