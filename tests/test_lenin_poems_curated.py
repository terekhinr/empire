"""Качество сборника стихов о Ленине для «Сказка на ночь»."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data" / "lenin_poems_curated.json"
BEDTIME = ROOT / "data" / "lenin_bedtime_stories.json"

_SPACED_RE = re.compile(r"(?:[А-ЯЁ]\s+){4,}[А-ЯЁ]")


def test_curated_has_all_catalog_poems():
    data = json.loads(CURATED.read_text(encoding="utf-8"))
    nums = {e["catalog_num"] for e in data["entries"]}
    assert len(nums) >= 60, f"too few catalog poems: {len(nums)}"
    assert all(e.get("author") and e.get("quote") for e in data["entries"])


def test_curated_no_ocr_garbage():
    data = json.loads(CURATED.read_text(encoding="utf-8"))
    for e in data["entries"]:
        q = e["quote"]
        assert "Д ж а м б у л" not in q
        assert "жирши1" not in q
        assert not _SPACED_RE.search(q), e.get("id")


def test_bedtime_poems_from_curated_not_pdf_ocr():
    bedtime = json.loads(BEDTIME.read_text(encoding="utf-8"))
    poems = [e for e in bedtime["entries"] if e.get("tag") == "стихи"]
    assert len(poems) >= 64
    for e in poems:
        q = e["quote"]
        assert "Н и к о л а и Б р а у н" not in q
        assert "Д ж а м б у л" not in q
        assert e.get("author") != "сборник"
