from __future__ import annotations

import os

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from prepare_md_for_tts import prepare_for_tts
from ru_tts.pipeline import RuTtsPipeline


def active_stress_marker() -> str:
    fmt = os.getenv("PDF_AUDIO_STRESS_FORMAT", "acute").lower()
    return {"plus": "+", "acute": "\u0301"}.get(fmt, "\u0301")


def plain(prepared: str) -> str:
    return prepared.replace("\u0301", "").replace("+", "")


def has_stress(prepared: str, base: str, vowel_idx: int) -> bool:
    """True if base[vowel_idx] carries the active stress marker in prepared."""
    prepared = prepared.casefold()
    base = base.casefold()
    assert base[vowel_idx].lower() in "аеёиоуыэюя", (base, vowel_idx)
    marker = active_stress_marker()
    if marker == "\u0301":
        stressed = base[:vowel_idx] + base[vowel_idx] + marker + base[vowel_idx + 1 :]
    else:
        stressed = base[:vowel_idx] + marker + base[vowel_idx:]
    return stressed in prepared



@pytest.mark.defect
def test_title_pause():
    prepared = prepare_for_tts("Заголовок\n\nТекст.")
    assert prepared.count("sil<[") + prepared.count("<break") == 1
    assert "Заголовок" in plain(prepared) and "Текст." in plain(prepared)
    assert "sil<[700]>" in prepared or '<break time="700ms"/>' in prepared


@pytest.mark.defect
def test_particle_to_is_spaced():
    assert "слово то сказано" in plain(prepare_for_tts("слово-то сказано"))


@pytest.mark.defect
def test_abbreviations_and_uw():
    assert "остров Сахалин" in plain(prepare_for_tts("О. Сахалин"))
    assert "уважаемые граждане" in plain(prepare_for_tts("ув. граждане"))
    assert "уважаемая Иванова Мария" in plain(prepare_for_tts("ув. Иванова Мария"))
    assert "уважаемому Иванову Сергею" in plain(prepare_for_tts("ув. Иванову Сергею"))


@pytest.mark.defect
def test_years():
    assert "тысяча девятьсот" in plain(prepare_for_tts("1964 г."))
    assert "с тысяча девятьсот" in plain(prepare_for_tts("1964-1967 г.г."))


# Pre-baseline manual verification: all #5 stress indices were checked against
# prepare_for_tts output; every indexed character is a Russian vowel.
@pytest.mark.defect
def test_surname_stress_and_city_contrast():
    assert has_stress(prepare_for_tts("Иванов Сергей"), "Иванов", 2)
    assert has_stress(prepare_for_tts("Иванова Мария"), "Иванова", 2)
    assert has_stress(prepare_for_tts("Иван Сергеевич"), "Иван", 2)
    dictionary = (Path(__file__).resolve().parents[1] / "scripts" / "tts_pronunciation_dict.txt").read_text(encoding="utf-8").casefold()
    assert "иван =" not in dictionary and "иваново =" not in dictionary
    assert has_stress(prepare_for_tts("город Иваново"), "Иваново", 2)


@pytest.mark.defect
def test_foreign_name_stability():
    values = [prepare_for_tts("Урсула фон дер Ляйнен") for _ in range(3)]
    assert values[0] == values[1] == values[2]
    assert "фон-дер" in plain(values[0])
    assert has_stress(values[0], "Урсула", 0)
    assert has_stress(values[0], "Ляйнен", 1)


@pytest.mark.defect
def test_hyphenated_toponym_is_not_split():
    pipeline = RuTtsPipeline(workdir=Path("/tmp/empire-tts-fix-cases"))
    prepared = prepare_for_tts("Рио-де-Жанейро")
    assert "Рио-де-Жанейро" in plain(prepared)
    assert all("Рио-де-Жанейро" in plain(chunk) for chunk in pipeline.chunk_text(prepared))


@pytest.mark.defect
def test_yo_and_homograph_contrasts():
    assert "Королёва Мария" in plain(prepare_for_tts("Королева Мария"))
    assert "шахматная королева" in plain(prepare_for_tts("шахматная королева"))
    assert "все пришли" in plain(prepare_for_tts("все пришли"))
    assert "всё хорошо" in plain(prepare_for_tts("всё хорошо"))


@pytest.mark.defect
def test_roman_numerals():
    assert "Иван Первый" in plain(prepare_for_tts("Иван I"))
    assert "том II" in plain(prepare_for_tts("том II"))
    # Existing normalizer intentionally expands this gold-covered form; do not alter it in Batch A.
    assert "девятнадцатый" in plain(prepare_for_tts("век XIX"))
