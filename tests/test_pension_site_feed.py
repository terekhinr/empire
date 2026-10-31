"""Дедуп ленты pension для сайта."""

from pension_site_feed import dedupe_pension_posts, pension_title_key


def test_title_key_normalizes_quotes():
    a = pension_title_key('<b>«Кем быть?»</b>')
    b = pension_title_key("<b>Кем быть?</b>")
    assert a == b


def test_dedupe_keeps_first_by_order():
    class P:
        def __init__(self, i, t):
            self.id = i
            self.text_content = t

    rows = [
        P(1, "<b>Кем быть?</b> текст один"),
        P(2, "<b>Кем быть?</b> текст два"),
        P(3, "<b>Вести с полей</b> иное"),
    ]
    out = dedupe_pension_posts(rows)
    assert [p.id for p in out] == [1, 3]
