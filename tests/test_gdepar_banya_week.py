"""Баня недели: TG ↔ карта."""

from pathlib import Path

import pytest

import gdepar_content

_HAVE_DB = (Path(__file__).resolve().parents[1] / "empire.db").is_file()


@pytest.mark.skipif(not _HAVE_DB, reason="empire.db отсутствует")
def test_pick_spot_for_tg_teaser():
    spot = gdepar_content.pick_spot_for_tg_teaser()
    assert spot is not None
    assert spot.get("slug")
    assert spot.get("title")


@pytest.mark.skipif(not _HAVE_DB, reason="empire.db отсутствует")
def test_banya_week_topic_contains_slug():
    topic = gdepar_content.build_banya_week_topic()
    assert "[Баня недели]" in topic
    assert "spot:" in topic or "fallback" in topic.lower()


def test_duo_dialog_block_for_practice():
    block = gdepar_content.duo_dialog_prompt_block("[Печи] Камни и трещины")
    assert "Михалыч" in block and "Кириллыч" in block


def test_kirilych_template_only():
    assert gdepar_content.kirilych_template_opening("Кириллыч, слушай — печь топить")
    assert not gdepar_content.kirilych_template_opening(
        "<b>Михалыч:</b> пар норм.\n<b>Кириллыч:</b> печь на 8 кВт."
    )
