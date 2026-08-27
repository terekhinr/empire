"""Ручные монологи Гдепар — без LLM."""

import asyncio

import gdepar_mono_curated as gmono


def test_all_hand_entries_publishable():
    data = gmono._load_data()
    entries = data.get("entries") or []
    assert len(entries) >= 8
    for e in entries:
        assert gmono._publishable(e), e.get("id")


def test_pick_entry_practice_pool():
    e = gmono.pick_entry(pool="practice")
    assert e is not None
    assert e.get("pool") == "practice"
    assert "body_html" in e
    assert "Михалыч" in e["body_html"] or "Кириллыч" in e["body_html"]


def test_build_slot_prebuilt():
    topic, body, img = asyncio.run(gmono.build_mono_curated_slot(pool="evening"))
    assert "[Монолог]" in topic
    assert "Михалыч" in body or "Кириллыч" in body or "fallback" in body.lower()
    assert "<b>" in body or "fallback" in body.lower()
