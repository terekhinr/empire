import asyncio
import json
from pathlib import Path

import stern_athletic_legacy as sal
import stern_content


def test_athletic_legacy_json_has_200_entries():
    p = Path(__file__).resolve().parents[1] / "data" / "stern_athletic_legacy.json"
    assert p.is_file(), "run tools/build_stern_athletic_legacy.py first"
    data = json.loads(p.read_text(encoding="utf-8"))
    entries = data["rubrics"]["athletic_legacy"]["entries"]
    ready = [e for e in entries if e.get("status") == "ready"]
    queued = [e for e in entries if e.get("status") == "queued"]
    assert len(ready) == 160
    assert len(ready) + len(queued) == len(entries)
    assert len(entries) >= 190


def test_format_ready_post_structure():
    entry = {
        "headline": "Иван Поддубный: Чемпион чемпионов",
        "bio": "Биография.",
        "facts": ["Факт 1.", "Факт 2."],
        "legacy": "Наследие.",
        "source": "Тест",
        "tag": "поддюбный",
        "status": "ready",
    }
    html = sal.format_athletic_legacy_post(entry)
    assert "Короткая биография" in html
    assert "Интересные факты" in html
    assert "Наследие" in html
    assert "#снегири" in html


def test_resolve_athletic_legacy_prebuilt():
    async def _fake(_p, _s):
        return "should not run"

    topic, prebuilt, img, seed = asyncio.run(
        stern_content.resolve_stern_slot(
            {"type": "stern_rubric", "rubric": "athletic_legacy"},
            weekday=1,
            resolve_topic_fn=_fake,
        )
    )
    assert "[Историческое наследие]" in topic
    assert prebuilt or seed
    if prebuilt:
        assert "биография" in prebuilt.lower() or "Биография" in prebuilt
