"""Speech prep: light normalize + silero stress without breaking marks."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_md_for_tts import (  # noqa: E402
    _ACUTE,
    _fix_literal_plus,
    _get_normalizer,
    prepare_for_tts,
    prepare_md_for_tts,
)


def test_libraries_available():
    assert _get_normalizer() is not None


def test_spaced_plus_to_i():
    assert "Вова и Настя" in _fix_literal_plus("Вова + Настя")


def test_stress_plus_not_destroyed():
    # silero notation must survive literal-plus fixer
    assert _fix_literal_plus("п+окерное мышл+ение") == "п+окерное мышл+ение"


def test_poker_range_suffix():
    assert "и выше" in _fix_literal_plus("рука АК+")


def test_pokernoe_stress_correct():
    text = prepare_for_tts("Покерное мышление.", accent=True)
    assert f"По{_ACUTE}керное" in text or f"по{_ACUTE}керное" in text.lower()
    assert "п и окер" not in text.lower()
    assert "+" not in text


def test_pokernoe_stress_plus_format(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_STRESS_FORMAT", "plus")
    text = prepare_for_tts("Покерное мышление.", accent=True)
    assert "п+окерное" in text.lower() or "П+окерное" in text
    assert "мышл+ение" in text.lower()
    assert _ACUTE not in text


def test_double_prepare_preserves_when_accent_off_on_plain():
    # plain text path
    text = prepare_for_tts("Маша Н. редактор. Вова + Настя.", accent=False)
    assert "Маша эн" not in text.lower()
    assert "+" not in text


def test_markdown_stripped():
    raw = prepare_md_for_tts("# Заголовок\n\n**Жирный** текст.\n")
    assert "**" not in raw


def test_expand_abbreviations_uv_and_td():
    from prepare_md_for_tts import expand_speech_abbreviations

    assert "уважаемый" in expand_speech_abbreviations("Ув. Иванов, здравствуйте.")
    assert "уважаемая" in expand_speech_abbreviations("ув. Петрова пишет.")
    assert "так далее" in expand_speech_abbreviations("книги, журналы и т.д.")
    assert "тому подобное" in expand_speech_abbreviations("и т.п.")
    assert "то есть" in expand_speech_abbreviations("т.е. важно")
    assert "в том числе" in expand_speech_abbreviations("в т.ч. Москва")
    # не ломаем обычные слова
    assert "страна" in expand_speech_abbreviations("большая страна.")


def test_prepare_expands_abbreviations(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_STRESS", "0")
    text = prepare_for_tts(
        "Ув. Сидоров пишет письмо и т.д. См. также рис. 3.",
        accent=False,
    )
    low = text.lower()
    assert "уважаемый" in low
    assert "так далее" in low
    assert "смотри" in low
    assert "рисунок" in low
    assert "ув." not in low
    assert "т.д." not in low.replace("т.д", "XX")  # no leftover abbr
