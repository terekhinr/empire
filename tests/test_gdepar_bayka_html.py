"""Рендер байок на gdepar.ru: blockquote и URL картинок."""

from gdepar_app import post_media_url, safe_post_html


def test_safe_post_html_renders_blockquote():
    raw = "📖 <b>Классическая баня</b>\n\n<blockquote>Цитата</blockquote>"
    out = str(safe_post_html(raw))
    assert "<blockquote>Цитата</blockquote>" in out
    assert "&lt;blockquote&gt;" not in out


def test_post_media_url_relative_and_absolute():
    assert post_media_url("media/draft_1.jpg") == "/media/draft_1.jpg"
    abs_path = "/root/projects/empire/media/gdepar/classic/x.jpg"
    assert post_media_url(abs_path) == "/media/gdepar/classic/x.jpg"
