"""Legal-form expansion + pronunciation lexicon for TTS."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_md_for_tts import expand_speech_abbreviations, prepare_for_tts  # noqa: E402
from tts_pronunciation import (  # noqa: E402
    apply_pronunciation_lexicon,
    expand_legal_forms,
    load_pronunciation_dict,
)


def test_ao_expands_to_company():
    import re

    text = expand_legal_forms('АО «Газпром» и ООО Ромашка')
    assert "акционерное общество" in text
    assert "общество с ограниченной ответственностью" in text
    assert re.search(r"(?<![А-Яа-яЁё])АО(?![А-Яа-яЁё])", text) is None
    assert re.search(r"(?<![А-Яа-яЁё])ООО(?![А-Яа-яЁё])", text) is None


def test_geo_ao_not_company():
    text = expand_legal_forms("Ненецкий АО и Еврейская АО рядом с Чукотским АО")
    assert "Ненецкий автономный округ" in text
    assert "Еврейская автономная область" in text
    assert "Чукотским автономный округ" in text
    assert "акционерное общество" not in text


def test_pao_zao_oao_ip():
    text = expand_legal_forms("ПАО Сбер, ЗАО Тест, ОАО Старое, ИП Иванов")
    assert "публичное акционерное общество" in text
    assert "закрытое акционерное общество" in text
    assert "открытое акционерное общество" in text
    assert "индивидуальный предприниматель" in text


def test_expand_speech_includes_legal():
    text = expand_speech_abbreviations("Ув. Иванов купил акции АО Тест и т.д.")
    assert "уважаемый" in text
    assert "акционерное общество" in text
    assert "так далее" in text


def test_mnogo_phoneme_when_enabled(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "1")
    mapping = {"много": "[[m n ɔ g ʌ]]", "немного": "[[nʲ ɪ m n ɔ g ʌ]]"}
    out = apply_pronunciation_lexicon("У нас много и немного воды.", mapping)
    assert "[[m n ɔ g ʌ]]" in out
    assert "[[nʲ ɪ m n ɔ g ʌ]]" in out
    assert "много" not in out.replace("[[m n ɔ g ʌ]]", "")


def test_mnogo_phoneme_skipped_without_flag(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "0")
    mapping = {"много": "[[m n ɔ g ʌ]]", "замок": "зам+ок"}
    out = apply_pronunciation_lexicon("много замков и замок", mapping)
    assert "[[m n ɔ g ʌ]]" not in out
    assert "много" in out
    assert "зам+ок" in out


def test_lexicon_matches_stressed_plus_form(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "1")
    mapping = {"много": "[[m n ɔ g ʌ]]"}
    out = apply_pronunciation_lexicon("здесь мн+ого снега", mapping)
    assert out == "здесь [[m n ɔ g ʌ]] снега"


def test_default_dict_loads():
    d = load_pronunciation_dict()
    assert "много" in d
    assert d["много"].startswith("[[")
    assert "со стороны" in d


def test_so_storony_stress_phrase(monkeypatch):
    """со стороны́ (род.) — не сто́роны (им. мн.)."""
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "0")
    from tts_pronunciation import clear_pronunciation_cache

    clear_pronunciation_cache()
    out = apply_pronunciation_lexicon(
        "Это было со стороны банка. Две стороны спора. С одной стороны верно."
    )
    assert "со сторон+ы" in out
    assert "с одной сторон+ы" in out
    # им.п. мн. «две стороны» не трогаем жёстким сторон+ы без предлога
    assert "Две стороны" in out or "две стороны" in out
    assert "ст+ороны" not in out  # не навязываем неверное ударение на о


def test_lexicon_overrides_misplaced_silero_plus(monkeypatch):
    """Эталон словаря полностью заменяет кривой + от silero (не двойной плюс)."""
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "0")
    from tts_pronunciation import clear_pronunciation_cache

    clear_pronunciation_cache()
    out = apply_pronunciation_lexicon("жалоба со сто+роны банка и звук орг+ана")
    assert "со сторон+ы" in out
    assert "сто+роны" not in out
    assert "сто+рон+ы" not in out
    assert "звук +органа" in out
    assert "орг+ана" not in out


def test_prepare_for_tts_ao_and_mnogo(monkeypatch):
    import re

    monkeypatch.setenv("PDF_AUDIO_STRESS", "0")
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "1")
    monkeypatch.setenv("PDF_AUDIO_TTS_PROVIDER", "yandex")
    text = prepare_for_tts(
        'АО «Вектор» продало много акций.',
        accent=False,
    )
    low = text.lower()
    assert "акционерное общество" in low
    assert "[[m n ɔ g ʌ]]" in text
    assert re.search(r"(?<![А-Яа-яЁё])АО(?![А-Яа-яЁё])", text) is None
