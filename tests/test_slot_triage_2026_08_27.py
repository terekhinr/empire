"""Триаж 2026-08-27: не ставить слоты без медиа и не спамить Ленина."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _live_types() -> set[str]:
    cfg = json.loads((ROOT / "content_config.json").read_text(encoding="utf-8"))
    found: set[str] = set()
    for key, block in cfg.items():
        if key.startswith("_") or not isinstance(block, dict):
            continue
        topics = block.get("topics") or {}
        for day in topics.values():
            if not isinstance(day, dict):
                continue
            for slot in day.values():
                if isinstance(slot, dict) and slot.get("type"):
                    found.add(str(slot["type"]))
    return found


def test_killed_slots_not_in_live_schedule():
    types = _live_types()
    # duo_curated снова в матрице (Ср–Вс 11:00) с fallback на mono без картинок
    assert "duo_curated" in types
    assert "stern_curated" not in types
    assert "stern_technique" not in types
    assert "lenin_calendar" not in types
    assert "lenin_pss" not in types


def test_lenin_one_slot_per_day():
    cfg = json.loads((ROOT / "content_config.json").read_text(encoding="utf-8"))
    assert cfg["lenin"]["schedule"] == ["12:00"]
    for day in range(7):
        bucket = cfg["lenin"]["topics"][str(day)]
        assert list(bucket.keys()) == ["12:00"]
        assert bucket["12:00"]["type"] == "lenin_rubric"


def test_stern_only_legacy():
    cfg = json.loads((ROOT / "content_config.json").read_text(encoding="utf-8"))
    assert cfg["stern"]["schedule"] == ["10:00"]
    assert cfg["stern"]["topics"]["1"]["10:00"]["rubric"] == "athletic_legacy"
    assert cfg["stern"]["topics"]["3"]["10:00"]["rubric"] == "athletic_legacy"


def test_dead_rubrics_autopublish_off():
    ap = json.loads((ROOT / "data" / "auto_publish.json").read_text(encoding="utf-8"))
    assert ap["rubrics"]["gdepar_duo_curated"]["enabled"] is True
    assert ap["rubrics"]["stern_curated"]["enabled"] is False
    assert ap["rubrics"]["stern_technique_video"]["enabled"] is False
    assert "[Историческое наследие]" not in (ap["rubrics"]["stern_curated"].get("topic_markers") or [])
    leg = ap["rubrics"]["stern_athletic_legacy"]
    assert leg["enabled"] is True
    assert "[Историческое наследие]" in leg["topic_markers"]
