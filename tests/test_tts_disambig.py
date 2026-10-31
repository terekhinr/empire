"""P3 homograph disambiguation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from tts_disambig import (  # noqa: E402
    apply_homograph_disambiguation,
    disambiguate_stoit,
    disambiguate_storony,
    disambiguate_zamok,
)


def test_storony_plural_vs_genitive():
    assert "ст+ороны" in disambiguate_storony("две стороны спора")
    assert "сторон+ы" in disambiguate_storony("со стороны банка")
    assert "сторон+ы" in disambiguate_storony("с одной стороны")


def test_zamok_lock_vs_castle():
    assert "зам+ок" in disambiguate_zamok("дверь на замок")
    assert "з+амок" in disambiguate_zamok("старинный замок короля")
    assert "з+амок" in disambiguate_zamok("замок короля на скале")


def test_stoit_cost_vs_stand():
    assert "ст+оит" in disambiguate_stoit("сколько стоит билет")
    assert "ст+оит" in disambiguate_stoit("это не стоит того")
    assert "сто+ит" in disambiguate_stoit("он стоит у окна")
    assert "сто+ит" in disambiguate_stoit("дом стоит на холме")


def test_pipeline_order(monkeypatch):
    import os

    sys.path.insert(0, str(ROOT / "scripts"))
    monkeypatch.setenv("PDF_AUDIO_STRESS", "0")
    monkeypatch.setenv("PDF_AUDIO_PHONEMES", "0")
    monkeypatch.setenv("PDF_AUDIO_DISAMBIG", "1")
    monkeypatch.setenv("PDF_AUDIO_PROSODY", "0")
    from prepare_md_for_tts import prepare_for_tts
    from tts_pronunciation import clear_pronunciation_cache

    clear_pronunciation_cache()
    text = prepare_for_tts(
        "Две стороны. Со стороны банка. На замок. Старинный замок. Сколько стоит. Он стоит у двери.",
        accent=False,
    )
    assert "ст+ороны" in text
    assert "сторон+ы" in text
    assert "зам+ок" in text
    assert "з+амок" in text
    assert "ст+оит" in text
    assert "сто+ит" in text
