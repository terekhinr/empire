"""P0 июнь 2026: хэштеги, анти-Кириллыч, автопост-конфиг."""

import json
from pathlib import Path

import gdepar_content
from main import _default_hashtag_line, _merge_hashtag_line


def test_stern_hashtag_limit_three():
    line = _merge_hashtag_line(
        ["#гири", "#здоровье", "#спина", "#офис", "#тренировка", "#кор"],
        "stern",
        "Биомеханика",
        topic_raw="[Биомеханика] Поясница",
    )
    tags = [t for t in line.split() if t.startswith("#")]
    assert len(tags) <= 3


def test_strip_kirilych_opening():
    raw = "🔥 Кириллыч, смотри — печь топить взялся.\n\nДрова сухие."
    out = gdepar_content.strip_kirilych_opening(raw)
    assert "кириллыч" not in out[:40].lower()
    assert "Дрова сухие" in out


def test_kirilych_opening_flagged_in_preachy():
    findings = gdepar_content.preachy_findings(
        "Кириллыч, вот тебе план по венику.", "[Веники] Берёза"
    )
    assert any("Кириллыч" in f for f in findings)


def test_lenin_garden_autopublish_enabled():
    cfg = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "auto_publish.json").read_text(
            encoding="utf-8"
        )
    )
    assert cfg["enabled"] is True
    assert cfg["personas"]["lenin"]["enabled"] is True
    assert cfg["personas"]["garden"]["enabled"] is True
    assert cfg["personas"]["gdepar"]["enabled"] is True
    assert cfg["personas"]["stern"]["enabled"] is True
    assert cfg["rubrics"]["gdepar_duo_curated"]["enabled"] is True
    assert cfg["rubrics"]["stern_matrix_curated"]["enabled"] is True


def test_stern_default_hashtags_short():
    line = _default_hashtag_line("stern", None)
    assert line.count("#") <= 3
