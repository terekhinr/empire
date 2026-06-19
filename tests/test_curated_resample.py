import asyncio

import rubric_posts


def test_parse_entry_id():
    assert rubric_posts.parse_entry_id_from_topic("[Классическая баня] Чехов (id=chekhov_ovrag)") == "chekhov_ovrag"


def test_curated_resample_gdepar():
    topic, text, img = asyncio.run(
        rubric_posts.curated_resample(
            "gdepar",
            "[Классическая баня] И.А. Гончаров, «Обломов» (id=goncharov_oblomov)",
        )
    )
    assert topic and text and "Классическая баня" in text
    assert "blockquote" in text
    assert "id=" in topic


def test_curated_resample_lenin():
    topic, text, _img = asyncio.run(
        rubric_posts.curated_resample(
            "lenin",
            "[Ленин · биография] Данилкин (id=bio_danilkin_paris)",
        )
    )
    assert topic and text
    assert "[Ленин · биография]" in topic
