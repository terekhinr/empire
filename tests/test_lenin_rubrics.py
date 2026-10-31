import asyncio
import json
from pathlib import Path

import lenin_content


def test_lenin_rubrics_json():
    p = Path(__file__).resolve().parents[1] / "data" / "lenin_rubrics.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    for key in ("literature", "art", "biography", "cinema"):
        assert len(data["rubrics"][key]["entries"]) >= 3


def test_film_still_only_after_manual_mark():
    film = {
        "image_file": "October film Lenin.jpg",
        "image_kind": "film_still",
    }
    assert lenin_content.resolved_lenin_image_file(film) == "Vladimir Lenin, 1917.jpg"
    film["image_approved"] = True
    assert lenin_content.resolved_lenin_image_file(film) == "October film Lenin.jpg"
    monument = {
        "image_file": "Monument to Lenin on Lenin Square in Volgograd.jpg",
        "image_kind": "monument",
    }
    assert "Monument to Lenin" in lenin_content.resolved_lenin_image_file(monument)


def test_rotation():
    assert lenin_content.rubric_key_for_weekday(0) == "literature"
    assert lenin_content.rubric_key_for_weekday(1) == "art"


def test_format_post():
    entry = {
        "quote": "Полная цитата для поста о Ленине в литературе.",
        "source": "Автор, книга",
        "note": "Комментарий редактора — не в канал.",
        "tag": "тест",
    }
    body = lenin_content.format_rubric_post("literature", entry)
    assert "Ленин в литературе" in body
    assert "blockquote" in body
    assert "Источник" in body
    assert "Комментарий" not in body


def test_lenin_cliche_detects_sim_pobedish():
    f = lenin_content.cliche_findings("Ленин пишет: Сим победиши.", "")
    assert any("сим победиши" in x for x in f)


def test_resolve_rubric_slot_returns_prebuilt_html():
    topic, prebuilt, img, seed = asyncio.run(
        lenin_content.resolve_lenin_slot({"type": "lenin_rubric", "rubric": "cinema"}, weekday=3)
    )
    assert seed is None
    assert prebuilt
    assert "blockquote" in prebuilt
    assert "[Ленин в кино]" in topic


def test_press_polemic_story_detected():
    text = (
        "Ленин о полемике: как издания теряют читателей. "
        "В 1912 году к коллективу «Невской Звезды» — нужно больше обсуждений в газетах."
    )
    assert lenin_content.is_press_polemic_story(text)
    findings = lenin_content.cliche_findings(text, "")
    assert any("полемик" in f or "газет" in f for f in findings)


def test_channel_support_only_revolution_variant():
    topic, body = lenin_content.build_channel_support_post()
    assert "мировую революцию" in body
    assert "Экстремизма" not in body
    assert "Победа в одном канале" not in body


def test_bedtime_story_prebuilt_no_llm():
    topic, body = lenin_content.build_bedtime_story_post()
    assert "Сказка на ночь" in topic
    assert "blockquote" in body
    assert "Источник:" in body


def test_resolve_lenin_book_slot_prebuilt():
    topic, prebuilt, img, seed = asyncio.run(
        lenin_content.resolve_lenin_slot({"type": "lenin_book"}, weekday=1)
    )
    assert seed is None
    assert prebuilt
    assert "Сказка на ночь" in topic


def test_verbatim_danilkin_shows_commentary_only_from_field():
    entry = {
        "quote": "«Цитата из Данилкина дословно.»",
        "source": "Л. Данилкин, «Ленин» (2017)",
        "verbatim": True,
        "commentary": "Короткий комментарий из той же книги.",
        "tag": "данилкин",
    }
    body = lenin_content.format_rubric_post("biography", entry)
    assert "blockquote" in body
    assert "Короткий комментарий" in body


def test_rubric_expansion_block_mentions_anchor():
    import rubric_posts

    seed = rubric_posts.make_rubric_seed(
        persona="lenin",
        rubric_key="literature",
        title="Ленин в литературе",
        emoji="📚",
        entry={"id": "x", "quote": "Тестовый тезис для якоря.", "source": "Автор, книга"},
    )
    block = rubric_posts.rubric_expansion_prompt_block(seed)
    assert "ЖЁСТКИЙ ЯКОРЬ" in block
    assert "550" in block or "950" in block


def test_pick_entry_no_repeat_within_cycle(tmp_path):
    import rubric_posts

    data = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "lenin_rubrics.json").read_text(
            encoding="utf-8"
        )
    )
    hist = tmp_path / "used.json"
    hist.write_text("{}", encoding="utf-8")
    for key in ("cinema", "art"):
        n = len(data["rubrics"][key]["entries"])
        seen = []
        for _ in range(n):
            e = rubric_posts.pick_entry(
                Path(__file__).resolve().parents[1] / "data" / "lenin_rubrics.json",
                hist,
                rubric=key,
            )
            seen.append(e["id"])
        assert len(seen) == len(set(seen)), seen
