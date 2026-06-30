"""P0-брак и stern_curated."""

import json
from pathlib import Path

import content_p0
import stern_curated as sc


def test_p0_catches_yoga_garbage():
    text = (
        "🔥 Йога для силовиков\n\n"
        "McGill пишет, что 85% травм у силовиков из-за потери контроля."
    )
    hits = content_p0.p0_findings(text, "stern")
    assert any("85%" in h for h in hits)
    assert any("McGill" in h for h in hits)


def test_p0_clean_stern_ok():
    text = (
        "🏛️ <b>Сброс пульса</b>\n\n"
        "Перед зумом дышу 4-4. Три цикла — голос ровнее.\n\n"
        "#снегири #штерн #дыхание"
    )
    assert content_p0.p0_findings(text, "stern") == []


def test_stern_curated_json_exists():
    p = Path(__file__).resolve().parents[1] / "data" / "stern_curated.json"
    if not p.is_file():
        return
    data = json.loads(p.read_text(encoding="utf-8"))
    entries = data.get("entries") or []
    assert len(entries) >= 50
    assert any(e.get("slot") == "0930" for e in entries)


def test_stern_curated_slot_type():
    assert sc.is_stern_curated_slot({"type": "stern_curated", "slot": "0930"})
    assert sc.slot_from_value({"type": "stern_curated", "slot": "1900"}) == "1900"
