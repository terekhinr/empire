"""Ручной дуэт Гдепар — без LLM."""

import asyncio

import gdepar_duo_curated as gduo


def test_pick_entry_practice_pool():
    e = gduo.pick_entry(pool="practice")
    assert e is not None
    assert e.get("pool") == "practice"
    assert "body_html" in e


def test_pick_banya_week_empty_returns_none():
    e = gduo.pick_entry(pool="banya_week")
    assert e is None


def test_build_slot_prebuilt():
    topic, body, img = asyncio.run(gduo.build_duo_curated_slot(pool="evening"))
    assert "[Дуэт]" in topic
    assert "Михалыч" in body or "fallback" in body.lower()
    assert "<b>" in body or "fallback" in body.lower()
