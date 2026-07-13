import asyncio
import json
from pathlib import Path

import stern_content


def test_stern_rubrics_json_valid():
    p = Path(__file__).resolve().parents[1] / "data" / "stern_rubrics.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    legacy_path = Path(__file__).resolve().parents[1] / "data" / "stern_athletic_legacy.json"
    legacy_data = json.loads(legacy_path.read_text(encoding="utf-8")) if legacy_path.is_file() else {}
    for key in stern_content.RUBRIC_ROTATION:
        if key == "athletic_legacy":
            src = legacy_data
        else:
            src = data
        active = [
            e
            for e in src["rubrics"][key]["entries"]
            if not e.get("deprecated") and (e.get("quote") or e.get("text") or e.get("seed"))
        ]
        assert len(active) >= 3


def test_kettlebell_history_no_empty_slogans():
    from rubric_posts import entry_quote

    p = Path(__file__).resolve().parents[1] / "data" / "stern_rubrics.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    for e in data["rubrics"]["kettlebell_history"]["entries"]:
        if e.get("deprecated"):
            continue
        q = entry_quote(e)
        assert len(q) >= 80
        assert "не спорит" not in (e.get("note") or "").lower()
        assert e.get("period") or e.get("author")


def test_rotation_five_rubrics():
    assert stern_content.rubric_key_for_weekday(0) == "kettlebell_history"
    assert stern_content.rubric_key_for_weekday(1) == "athletic_legacy"
    assert stern_content.rubric_key_for_weekday(4) == "sports_med"


def test_resolve_rubric_returns_prebuilt_not_llm():
    async def _fake(_p, _s):
        return "should not run"

    topic, prebuilt, img, seed = asyncio.run(
        stern_content.resolve_stern_slot(
            {"type": "stern_rubric", "rubric": "equipment"},
            weekday=0,
            resolve_topic_fn=_fake,
        )
    )
    assert seed is None
    assert prebuilt
    assert "<blockquote>" in prebuilt or "<b>" in prebuilt
    assert "Гиря" not in prebuilt[:40] or "не просто" not in prebuilt
    assert "[Экипировка" in topic


def test_resolve_normal_slot_delegates():
    async def _fake(_p, slot):
        return f"topic:{slot}"

    topic, text, img, seed = asyncio.run(
        stern_content.resolve_stern_slot(
            "[Техника] test",
            weekday=0,
            resolve_topic_fn=_fake,
        )
    )
    assert text is None
    assert seed is None
    assert "topic:" in topic
