"""NSW expansions + prosody pauses for TTS."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_md_for_tts import expand_speech_abbreviations, prepare_for_tts  # noqa: E402
from tts_nsw import apply_prosody_pauses, expand_nsw, sanitize_angle_brackets  # noqa: E402
from tts_pronunciation import apply_pronunciation_lexicon, clear_pronunciation_cache  # noqa: E402


def test_etc_to_et_setera():
    assert "эт сетера" in expand_speech_abbreviations("books, music, etc.")
    assert "эт сетера" in expand_nsw("foo etc bar")
    assert "etch" in expand_nsw("etch a sketch")  # не трогаем


def test_nsw_percent_and_money():
    out = expand_nsw("скидка 15% и цена $100")
    assert "процентов" in out
    assert "долларов" in out
    assert "%" not in out
    assert "$" not in out


def test_nsw_range_and_roman():
    out = expand_nsw("вес 10-15 кг в XXI веке")
    assert "от" in out and "до" in out
    assert "двадцать первый" in out.lower()
    assert "килограммов" in out


def test_prosody_to_comma():
    out = apply_prosody_pauses("он сказал то, чего не должен был говорить")
    assert "sil<[600]>" in out
    assert "—" in out
    assert "сказалто" not in out.replace(" ", "").replace("—", "")
    assert re.search(r"сказал\s+—\s+sil<\[600\]> то", out)
    out2 = apply_prosody_pauses("он сказ+ал то, чего не должен")
    assert "сказ+ал — sil<[600]> то" in out2
    # не трогаем «про то, как…»
    pro = apply_prosody_pauses("книга про то, как не сдаваться")
    assert "— sil<[600]> то" not in pro
    # голые скобки не должны остаться (→ «больше чем меньше чем»)
    assert "<>" not in apply_prosody_pauses("тест <> хвост")
    assert sanitize_angle_brackets("a <> b >< c") == "a b c"


def test_nishchepunk_stress(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "0")
    clear_pronunciation_cache()
    out = apply_pronunciation_lexicon("эстетика нищепанк и нищепанка")
    assert "нищеп+анк" in out
    assert "нищеп+анка" in out


def test_prepare_user_cases(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_STRESS", "0")
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "1")
    monkeypatch.setenv("PDF_AUDIO_TTS_PROVIDER", "yandex")
    monkeypatch.setenv("PDF_AUDIO_PROSODY", "1")
    clear_pronunciation_cache()
    text = prepare_for_tts(
        "Он сказал то, чего не должен. Жанр нищепанк, music etc. Со стороны банка.",
        accent=False,
    )
    low = text.lower()
    assert "эт сетера" in low
    assert "нищеп+анк" in low
    assert "сторон+ы" in low
    assert "sil<[600]>" in text and "—" in text


def test_euro_millions_not_spelled():
    from tts_nsw import expand_nsw

    out = expand_nsw("бюджет 15 € млн. на проект")
    assert "миллионов" in out
    assert "евро" in out
    assert "млн" not in out.lower()
    # число + шкала + валюта, не «евро млн»
    assert re.search(r"миллионов\s+евро", out, re.I)


def test_uv_gender_default_masculine():
    assert "уважаемый" in expand_speech_abbreviations("ув. пидорас курсор")
    assert "уважаемая" not in expand_speech_abbreviations("ув. пидорас курсор")
    assert "уважаемый" in expand_speech_abbreviations("ув. никита")
    assert "уважаемая" in expand_speech_abbreviations("ув. Петрова")
    assert "уважаемая" in expand_speech_abbreviations("ув. Мария")


def test_euro_millions_order():
    out = expand_nsw("бюджет 15 € млн. и €15 млн")
    assert "миллионов евро" in out
    assert "евро миллионов" not in out


def test_after_context_organ(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "0")
    clear_pronunciation_cache()
    out = apply_pronunciation_lexicon("звук органа, половой орган, просто орган")
    assert "звук +органа" in out
    assert "половой орг+ан" in out
    assert "просто орган" in out  # без контекста не трогаем


def test_heading_and_para_pauses(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_STRESS", "0")
    monkeypatch.setenv("PDF_AUDIO_PROSODY", "1")
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "0")
    text = prepare_for_tts("# Введение\n\nПервый абзац.\n\nВторой абзац.", accent=False)
    assert "sil<[800]>" in text
    assert "sil<[500]>" in text
