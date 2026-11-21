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
    assert "в тысяча девятьсот шестьдесят четвёртом году" in plain(prepare_for_tts("в 1964 г."))
    assert "в тысяча девятьсот шестьдесят четвёртом — тысяча девятьсот шестьдесят седьмом годах" in plain(prepare_for_tts("в 1964-1967 г.г."))


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
    assert "шахматная королева" in plain(prepare_for_tts("шахматная королева ходит"))


@pytest.mark.defect
def test_roman_numerals():
    assert "Иван Первый" in plain(prepare_for_tts("Иван I"))
    assert "том II" in plain(prepare_for_tts("том II"))
    # Existing normalizer intentionally expands this gold-covered form; do not alter it in Batch A.
    assert "девятнадцатый" in plain(prepare_for_tts("век XIX"))


# --- «Прыжок через акулу» (17 нояб, 2026-11-21) ---

@pytest.fixture
def plus_fmt(monkeypatch):
    monkeypatch.setenv("PDF_AUDIO_STRESS_FORMAT", "plus")


@pytest.mark.defect
@pytest.mark.parametrize(
    "src, expected",
    [
        ("Marketingcharts жалуется из 2026 на то, как это выглядит.", "из две тысячи двадцать шестого на то"),
        ("Hollywood Reporter жалуется нам из 2024.", "из две тысячи двадцать четвёртого."),
        ("чем в сезоне 2022-23 годов, согласно", "в сезоне две тысячи двадцать второго — две тысячи двадцать третьего годов"),
        ("рейтингам за 2023-24 годы.", "за две тысячи двадцать третий — две тысячи двадцать четвёртый годы"),
        ("в группе взрослых 18-49 лет по сравнению.", "взрослых от восемнадцати до сорока девяти лет"),
        ("за 5-7 дней.", "за пять-семь дней"),
        ("в 2-3 раза больше.", "в два-три раза больше"),
        ("на 2-3 недели.", "на две-три недели"),
        ("около 10-15 человек.", "около десяти-пятнадцати человек"),
        ("на 20-30% больше.", "на двадцать-тридцать процентов"),
        ("выросли 50-57%.", "от пятидесяти до пятидесяти семи процентов"),
        ("посмотрели в среднем 2,6 фильма. Согласно опросам.", "в среднем две целых шесть десятых фильма. Согласно"),
        ("составляло 4,3, это ниже.", "четыре целых три десятых,"),
        ("ниже показателя 7,0 в 1990-х.", "показателя семи в тысяча девятьсот девяностых"),
        ("в 1,5 раза больше.", "в полтора раза"),
        ("оценивался в 1,6 триллиона долларов.", "шесть десятых триллиона долларов"),
        ("в топе-10 проката 8/9 из 10 римейки.", "восемь-девять из десяти"),
        ("17 нояб 12:00", "семнадцатое ноября двенадцать ноль-ноль"),
        ("встреча в 12:30.", "в двенадцать тридцать"),
        ("около 15 человек.", "около пятнадцати человек"),
    ],
)
def test_numbers_from_shark_article(src, expected):
    assert expected in plain(prepare_for_tts(src))


@pytest.mark.defect
def test_numbers_untouched_cases():
    # «из 2024 опрошенных» — количество, не год
    assert "из двух тысяч двадцати четырёх опрошенных" in plain(prepare_for_tts("из 2024 опрошенных."))
    # даты-диапазоны не превращаем в количественные
    assert "от пяти до семи мая" not in plain(prepare_for_tts("в 5-7 мая."))


@pytest.mark.defect
@pytest.mark.parametrize(
    "src, stressed",
    [
        ("нужны опилки или трухлявые пни, кинокритике нужно кино.", "пн+и"),
        ("на самом пике его популярности.", "п+ике"),
        ("Я имею в виду, что новых фильмов. Я имею в виду, что где-то.", "в в+иду"),
        ("украсть друг у дружки креатив.", "др+ужки"),
        ("имена Ямвлиха или Афинея?", "Аф+инея"),
        ("сериал «Я люблю Люси».", "Л+юси"),
        ("а Фонзи прыгает.", "Ф+онзи"),
        ("собственные подкастеры и жаргон.", "подк+астеры"),
        ("на уже сложившемся «золотом фонде».", "золот+ом"),
    ],
)
def test_stress_from_shark_article(plus_fmt, src, stressed):
    assert stressed in prepare_for_tts(src)


@pytest.mark.defect
def test_vidu_never_wrong(plus_fmt):
    assert "вид+у" not in prepare_for_tts("Я имею в виду, что новых фильмов. Я имею в виду, что где-то.")


@pytest.mark.defect
def test_author_yo_is_kept(plus_fmt):
    assert "всё новые обработки" in plain(prepare_for_tts("изобретать всё новые обработки полёта."))
    assert "все новые сотрудники" in plain(prepare_for_tts("все новые сотрудники пришли."))
