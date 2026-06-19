"""Obsidian → Telegram HTML: цитаты, ссылки, wikilinks."""

from __future__ import annotations

import os

os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")

from main import fix_html_safety  # noqa: E402


def test_obsidian_md_link_and_blockquote():
    body = """[Новость](https://t.me/bbbreaking/230398)

> Фонд Совета мира остался **без финансирования**
> вторая строка цитаты

Войны никто не хочет.
https://www.sipri.org/media/press-release/2026/test
"""
    out = fix_html_safety(body)
    assert '<a href="https://t.me/bbbreaking/230398">' in out
    assert "<blockquote>" in out
    assert "Фонд Совета мира" in out
    assert "<b>без финансирования</b>" in out
    assert "> Фонд" not in out
    assert '<a href="https://www.sipri.org/media/press-release/2026/test">' in out


def test_obsidian_wikilink_external_and_internal():
    body = "См. [[https://example.com/doc|источник]] и [[growth-rf-2026#День]]."
    out = fix_html_safety(body)
    assert '<a href="https://example.com/doc">источник</a>' in out
    assert "growth-rf-2026" in out
    assert "[[growth" not in out


def test_obsidian_bare_tme_url():
    body = "Из свежего\nhttps://t.me/bbbreaking/229929\nСША могут."
    out = fix_html_safety(body)
    assert '<a href="https://t.me/bbbreaking/229929">' in out


def test_obsidian_markdown_table_to_list():
    body = """| № | Направление | Мест | Заявлений |
| --- | --- | --- | --- |
| 1 | Информатика | 38 916 | 869 158 |
| 2 | Экономика | 17 264 | 690 940 |
"""
    out = fix_html_safety(body)
    assert "<b>1.</b>" in out
    assert "Информатика" in out
    assert "<b>38 916</b>" in out
    assert "| --- |" not in out
    assert "<pre>" not in out


def test_obsidian_strike_and_image_embed_stripped():
    body = "~~Кукуруза~~ **Философия**\n\n![[Pasted image.png|491]]\n\nТекст."
    out = fix_html_safety(body)
    assert "<s>Кукуруза</s>" in out
    assert "<b>Философия</b>" in out
    assert "![[" not in out
    assert "Pasted image" not in out
