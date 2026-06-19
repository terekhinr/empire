"""Telegram HTML из Markdown (Obsidian, LLM) — валидные вложенные теги."""

from __future__ import annotations

import os

os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")

from main import fix_html_safety  # noqa: E402


def test_triple_asterisk_becomes_valid_bold_not_nested_mess():
    body = "***Можно ли покупать на новостях?***"
    out = fix_html_safety(body)
    assert "<b>Можно ли покупать на новостях?</b>" in out
    assert "</b></i>" not in out
    assert "</i></b>" not in out or out.index("</b>") > out.index("</i>") if "</i>" in out else True


def test_balance_fixes_wrong_close_order():
    broken = "<b><i>текст</b></i>"
    out = fix_html_safety(broken)
    assert out == "<b><i>текст</i></b>"


def test_pension_obsidian_sample_body():
    body = """***Можно ли покупать на новостях?***

Из свежего
https://t.me/bbbreaking/229929
США могут вновь ослабить ограничения."""

    out = fix_html_safety(body)
    assert "<b>Можно ли покупать на новостях?</b>" in out
    assert '<a href="https://t.me/bbbreaking/229929">' in out
    assert out.count("<b>") == out.count("</b>")
    assert out.count("<i>") == out.count("</i>")
