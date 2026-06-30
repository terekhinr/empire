"""Тесты разнообразия и спец-слотов gdepar."""

import json
from pathlib import Path

import pytest

import gdepar_content


def test_angle_families_detect():
    fam = gdepar_content.angle_families_for_text("[Психология] Тишина в парилке")
    assert "этикет_тишина" in fam


def test_family_penalty_increases_on_repeat():
    recent = ["[Психология] Тишина в парилке: нормы"]
    p1 = gdepar_content.family_penalty_score(recent, "[Медитация] Молчаливое парение")
    p2 = gdepar_content.family_penalty_score([], "[Медитация] Молчаливое парение")
    assert p1 >= p2


def test_promo_post_has_utm():
    _, body = gdepar_content.build_promo_map_post()
    assert "utm_source=telegram" in body
    assert "gdepar.ru" in body


def test_literature_json_valid():
    path = Path(__file__).resolve().parents[1] / "data" / "gdepar_literature.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["quotes"]) >= 3


def test_cliche_findings_outside_topic():
    f = gdepar_content.cliche_findings("В парилке тишина — священное правило.", "[Инженерия] Печь")
    assert any("клише" in x for x in f)


def test_venik_image_prompt_birch():
    p = gdepar_content.resolve_venik_image_prompt("[Веники] Берёза: запаривание.", provider="flux")
    assert p == gdepar_content.GDEPAR_VENIK_BIRCH_IMAGE_PROMPT
    assert "triangular fan" in p.lower() or "fan 35" in p.lower()
    assert "chives" in p.lower() or "grass stalks" in p.lower()
    assert "lathe-turned" in p.lower() or "dowel" in p.lower()
    assert "small leaves" not in p.lower()
    assert "venik dlya parenya" in p.lower()


def test_venik_image_prompt_birch_gemini():
    p = gdepar_content.resolve_venik_image_prompt("[Веники] Берёза: запаривание.", provider="gemini")
    assert p == gdepar_content.GDEPAR_VENIK_BIRCH_GEMINI_PROMPT
    assert "traditional birch sauna whisk" in p
    assert "Hyper-realistic, macro photography" in p


def test_venik_image_prompt_oak():
    p = gdepar_content.resolve_venik_image_prompt("[Веники] Дуб: время в воде.", provider="flux")
    assert p == gdepar_content.GDEPAR_VENIK_OAK_IMAGE_PROMPT
    assert "oak leaves" in p.lower()


def test_venik_image_prompt_oak_gemini():
    p = gdepar_content.resolve_venik_image_prompt("[Веники] Дуб: время в воде.", provider="gemini")
    assert p == gdepar_content.GDEPAR_VENIK_OAK_GEMINI_PROMPT
    assert "sturdy oak banya venik" in p
    assert "shallow depth of field" in p


def test_venik_image_provider_auto(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
    monkeypatch.setenv("GDEPAR_VENIK_IMAGE_PROVIDER", "auto")
    assert gdepar_content.venik_image_provider() == "flux"
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert gdepar_content.venik_image_provider() == "gemini"


def test_venik_flux_params():
    assert gdepar_content.GDEPAR_VENIK_FLUX["num_inference_steps"] >= 40
    assert gdepar_content.GDEPAR_VENIK_FLUX["guidance_scale"] >= 5.0


def test_venik_image_prompt_not_broom_topic():
    assert gdepar_content.resolve_venik_image_prompt("[Печи] Камни и трещины.") is None


def test_gdepar_image_prompt_stove_not_venik():
    p = gdepar_content.resolve_gdepar_image_prompt("[Печи] Камни и трещины.")
    assert p == gdepar_content.GDEPAR_STOVE_IMAGE_PROMPT


def test_health_topic_no_venik_despite_llm_whisk():
    topic = "[Здоровье] Сердце и баня: пульс и когда выйти."
    assert gdepar_content.resolve_venik_image_prompt(topic) is None
    p = gdepar_content.resolve_gdepar_image_prompt(topic)
    assert p == gdepar_content.GDEPAR_HEALTH_IMAGE_PROMPT


def test_llm_prompt_whisk_does_not_force_venik():
    assert gdepar_content.resolve_venik_image_prompt(
        "[Здоровье] Давление после пара."
    ) is None


def test_preachy_findings():
    f = gdepar_content.preachy_findings(
        "Кириллыч, не геройствуй. Пульс выше 140 — сразу выходи.",
        "[Здоровье] Сердце",
    )
    assert f


def test_filter_hashtags_drops_venik_on_health():
    out = gdepar_content.filter_hashtags_for_topic(
        "[Здоровье] Сердце",
        ["#Здоровье", "#Веник", "#Баня"],
    )
    assert "#Веник" not in out and "#Здоровье" in out


def test_resolve_promo_slot():
    import asyncio

    async def _fake(_p, _s):
        return "x"

    topic, prebuilt, img = asyncio.run(
        gdepar_content.resolve_gdepar_slot({"type": "promo_map"}, resolve_topic_fn=_fake)
    )
    assert prebuilt
    assert img is None
    assert "promo" in topic.lower() or "SPECIAL" in topic


def test_author_search_queries_surname():
    qs = gdepar_content._author_search_queries("Ф.М. Достоевский")
    assert any("Достоевский" in q for q in qs)
    assert any("portrait" in q for q in qs)


def test_portrait_url_rejects_banya():
    assert not gdepar_content._portrait_url_ok(
        "https://commons.wikimedia.org/wiki/Special:FilePath/Russian_banya.jpg"
    )
    assert gdepar_content._portrait_url_ok(
        "https://upload.wikimedia.org/wikipedia/commons/Dostoevsky.jpg"
    )


def test_classic_banya_json_valid():
    path = Path(__file__).resolve().parents[1] / "data" / "gdepar_classic_banya.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["entries"]) >= 18
    for e in data["entries"]:
        assert e.get("author") and (e.get("quote") or e.get("text"))
        assert e.get("image_url") or e.get("image_file")


def test_format_classic_post():
    entry = {
        "quote": "Тест цитаты достаточной длины для полноценного поста в канале.",
        "author": "А. Автор",
        "work": "«Книга»",
        "mikhalych": "Михалыч: да.",
        "tag": "тест",
    }
    body = gdepar_content.format_classic_banya_post(entry)
    assert "Классическая баня" in body
    assert "blockquote" in body
    assert "А. Автор" in body
    assert "#классика" in body


def test_resolve_classic_slot():
    import asyncio

    async def _fake(_p, _s):
        return "x"

    topic, prebuilt, _img = asyncio.run(
        gdepar_content.resolve_gdepar_slot({"type": "classic_banya"}, resolve_topic_fn=_fake)
    )
    assert prebuilt
    assert gdepar_content.CLASSIC_RUBRIC_TAG in topic
    assert "Классическая баня" in prebuilt
