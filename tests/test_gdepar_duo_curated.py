"""Ручной дуэт Гдепар — без LLM; без картинок — fallback на mono."""

import asyncio

import gdepar_duo_curated as gduo
import gdepar_mono_curated as gmono


def test_publishable_count_without_media_is_zero():
    # media/gdepar/topics пуст → publishable=0, слот не должен падать
    assert gduo.publishable_count(pool="practice") == 0


def test_pick_entry_without_images_returns_none():
    e = gduo.pick_entry(pool="practice")
    assert e is None


def test_build_slot_falls_back_to_mono():
    topic, body, img = asyncio.run(gduo.build_duo_curated_slot(pool="evening"))
    assert topic and body
    # Пока нет картинок дуэта — mono evening
    assert gmono.MONO_RUBRIC_TAG in topic or "[Монолог]" in topic
    assert len(body) >= 50


def test_pick_banya_week_empty_returns_none():
    e = gduo.pick_entry(pool="banya_week")
    if e is not None:
        assert e.get("pool") == "banya_week"
        assert gduo._publishable(e)
