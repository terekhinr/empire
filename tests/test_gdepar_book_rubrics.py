import asyncio

import gdepar_book_rubrics as gbr
import gdepar_content as gc


def test_book_rubric_format():
    entry = {
        "id": "test_1",
        "author": "Ю.М. Хошев",
        "work": "«Дачные бани и печи»",
        "chapter": "Введение",
        "quote": "Бани по-русски — это водные процедуры.",
        "note": "Короткий комментарий без морали.",
        "tag": "дача",
    }
    html = gbr.format_book_post(entry, "pechi_banya")
    assert "Хошев" in html
    assert "Михалыч" in html
    assert "#дача" in html


def test_resolve_book_rubric_slot():
    async def _fake(*_a, **_k):
        return "unused"

    topic, prebuilt, img = asyncio.run(
        gc.resolve_gdepar_slot(
            {"type": "book_rubric", "rubric": "pechi_banya"},
            resolve_topic_fn=_fake,
        )
    )
    assert prebuilt
    assert "[Печь и баня]" in topic
    assert "Хошев" in prebuilt or "fallback" in prebuilt.lower()


def test_is_book_rubric_slot():
    assert gbr.is_book_rubric_slot({"type": "book_rubric", "rubric": "pechi_banya"}) == "pechi_banya"
    assert gbr.is_book_rubric_slot({"type": "classic_banya"}) is None
