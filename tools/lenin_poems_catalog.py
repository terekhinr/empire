"""Каталог «Стихи о Ленине» (Школьная библиотека, 1974) — автор, название, страница."""

from __future__ import annotations

import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
POEMS_PDF = ROOT / "data" / "lenin" / "Стихи о Ленине (Школьная библиотека) — 1974.pdf"
WORK = "«Стихи о Ленине» (Школьная библиотека, 1974)"

# Ручная выверка по оглавлению (стр. 63–64 PDF); page = печатная страница книги.
CATALOG: list[dict] = [
    {"num": 1, "author": "В. Маяковский", "title": "Владимир Ильич Ленин", "note": "из поэмы", "page": 5},
    {"num": 2, "author": "С. Смирнов", "title": "Есть человек, и день его рожденья…", "page": 8},
    {"num": 3, "author": "М. Светлов", "title": "Ленин смотрит на нас", "page": 10},
    {"num": 4, "author": "С. Михалков", "title": "На родине Ленина", "note": "из поэмы", "page": 11},
    {"num": 5, "author": "С. Кирсанов", "title": "Читая Ленина", "page": 14},
    {"num": 6, "author": "С. Щипанёв", "title": "Домик в Шушенском", "note": "из поэмы", "page": 16},
    {"num": 7, "author": "В. Рождественский", "title": "Перед грозой", "page": 18},
    {"num": 8, "author": "Н. Тихонов", "title": "На паровозе", "note": "рассказ машиниста", "page": 20},
    {"num": 9, "author": "Н. Браун", "title": "Есть такая партия!", "page": 23},
    {"num": 10, "author": "А. Сурков", "title": "Покончив с тревогами жизни подпольной…", "page": 26},
    {"num": 11, "author": "Б. Кежун", "title": "У Смольного", "page": 27},
    {
        "num": 12,
        "author": "С. Михалков",
        "title": "Мы видим город Петроград…",
        "note": "из поэмы «В Музее В. И. Ленина»",
        "page": 29,
    },
    {"num": 13, "author": "И. Шамов", "title": "Солдатский хлеб", "note": "быль", "page": 31},
    {"num": 14, "author": "А. Яшин", "title": "У кабинета Ильича", "page": 33},
    {"num": 15, "author": "Я. Смеляков", "title": "Наш герб", "page": 35},
    {"num": 16, "author": "Г. Гоппе, В. Верховский", "title": "Разговор о тепле", "page": 38},
    {"num": 17, "author": "П. Железное", "title": "Дети Ленина", "page": 43},
    {"num": 18, "author": "М. Исаковский", "title": "Докладная записка", "note": "деревенская быль", "page": 45},
    {"num": 19, "author": "Я. Шведов", "title": "Застава Ильича", "page": 50},
    {"num": 20, "author": "И. Ринк", "title": "Площадь у Финляндского вокзала…", "page": 52},
    {"num": 21, "author": "А. Прокофьев", "title": "Ленин мужество вселил…", "note": "из «Сияны»", "page": 53},
    {"num": 22, "author": "П. Бровка", "title": "Декрет Ленина", "note": "пер. Я. Хелемского", "page": 54},
    {"num": 23, "author": "С. Орлов", "title": "Первая годовщина", "page": 56},
    {"num": 24, "author": "Я. Козловский", "title": "Депеша", "page": 58},
    {"num": 25, "author": "С. Орлов", "title": "Ленин в Кашине", "page": 60},
    {"num": 26, "author": "Л. Татьяничева", "title": "Самолёт, похожий на Икара", "page": 62},
    {"num": 27, "author": "Р. Гамзатов", "title": "Горцы у Ленина", "note": "пер. Н. Гребнева", "page": 63},
    {"num": 28, "author": "А. Твардовский", "title": "Ленин и печник", "page": 66},
    {"num": 29, "author": "В. Ауговской", "title": "Ленин", "page": 73},
    {"num": 30, "author": "В. Инбер", "title": "Пять ночей и дней", "page": 76},
    {"num": 31, "author": "Д. Бедный", "title": "Снежинки", "page": 77},
    {"num": 32, "author": "А. Безыменский", "title": "Партбилет №224332", "page": 78},
    {"num": 33, "author": "Я. Смеляков", "title": "Кремлёвские ели", "page": 79},
    {"num": 34, "author": "Х. Берулав", "title": "Ленину", "note": "пер. А. Межирова", "page": 80},
    {"num": 35, "author": "В. Инбер", "title": "Ленин и Время", "page": 81},
    {"num": 36, "author": "С. Эули", "title": "Я видел Ленина", "note": "пер. с грузинского", "page": 83},
    {"num": 37, "author": "Б. Кербабаев", "title": "Ленин", "note": "пер. Г. Веселкова", "page": 84},
    {"num": 38, "author": "И. Тобольский", "title": "Он смотрит вдаль спокойно и открыто…", "page": 85},
    {"num": 39, "author": "С. Орлов", "title": "Гвардейское знамя", "page": 86},
    {"num": 40, "author": "Н. Рыленков", "title": "Баллада о портрете", "page": 87},
    {"num": 41, "author": "С. Маршак", "title": "Баллада о памятнике", "page": 89},
    {"num": 42, "author": "М. Дудин", "title": "Стихи о шалаше", "page": 91},
    {"num": 43, "author": "И. Шамов", "title": "На дальнем рубеже", "page": 93},
    {
        "num": 44,
        "author": "К. Кулиев",
        "title": "…Я вечно славить Ленина готов…",
        "note": "из «Горской поэмы о Ленине»",
        "page": 95,
    },
    {
        "num": 45,
        "author": "Джамбул",
        "title": "…Неогляден степной простор…",
        "note": "из «От всего сердца», пер. К. Алтайского",
        "page": 96,
    },
    {"num": 46, "author": "М. Дудин", "title": "Ленин", "page": 97},
    {"num": 47, "author": "О. Дриз", "title": "Сандаловая палочка", "note": "пер. Т. Спендиаровой", "page": 98},
    {
        "num": 48,
        "author": "С. Хаким",
        "title": "Сердце беседует с Лениным",
        "note": "пер. Р. Морана",
        "page": 101,
    },
    {
        "num": 49,
        "author": "Б. Рахим-заде",
        "title": "Улица Ленина",
        "note": "пер. А. Ойслenderа",
        "page": 102,
    },
    {"num": 50, "author": "И. Гришашвили", "title": "Ленин", "note": "пер. Г. Павловского", "page": 104},
    {"num": 51, "author": "Е. Тараховская", "title": "Памятник Ленину", "page": 105},
    {"num": 52, "author": "З. Александрова", "title": "Музей Ленина в Праге", "page": 106},
    {"num": 53, "author": "В. Азаров", "title": "Легенда о фонарях", "page": 108},
    {
        "num": 54,
        "author": "Д. Джаббаров",
        "title": "В кабинете Ленина",
        "note": "пер. С. Северцева",
        "page": 110,
    },
    {
        "num": 55,
        "author": "М. Нугманов",
        "title": "Есть в России такие леса и поля…",
        "note": "из «Грозовое лето», пер. Р. Морана",
        "page": 111,
    },
    {"num": 56, "author": "Н. Саконская", "title": "В гостях у Ленина", "page": 113},
    {"num": 57, "author": "В. Инбер", "title": "О Ленине", "page": 115},
    {"num": 58, "author": "М. Лисянский", "title": "Космонавт приходит к Ильичу", "page": 116},
    {"num": 59, "author": "Л. Татьяничева", "title": "В кабине космонавта", "page": 117},
    {"num": 60, "author": "Ю. Яковлев", "title": "Ленин с нами", "page": 118},
    {"num": 61, "author": "М. Исаковский", "title": "101-й год", "page": 118},
    {
        "num": 62,
        "author": "С. Михалков",
        "title": "…Если вспомнить дни былые…",
        "note": "из поэмы «Будь готов»",
        "page": 120,
    },
    {"num": 63, "author": "Н. Тихонов", "title": "Неисчислимы Ленина портреты…", "page": 122},
    {
        "num": 64,
        "author": "В. Маяковский",
        "title": "Разве молнии велишь не литься?..",
        "note": "из «Мы не верим»",
        "page": 124,
    },
]

_LENINISM_BASE = "https://leninism.su/posetiteli-sajta-o-lenine/4189-stixi-o-lenine.html"

# Прямые URL — приоритетнее leninism/PDF (добавлять по мере нахождения).
EXTERNAL_URLS: list[dict] = [
    {"num": 3, "url": "https://rustih.ru/mixail-svetlov-lenin-smotrit-na-nas/"},
    {"num": 4, "url": "https://leninism.su/posetiteli-sajta-o-lenine/4189-stixi-o-lenine.html?start=4"},
    {"num": 5, "url": "https://rustih.ru/semyon-kirsanov-chitaya-lenina/"},
    {"num": 63, "url": "https://leninism.su/posetiteli-sajta-o-lenine/4189-stixi-o-lenine.html?start=63"},
]


def page_ranges() -> list[dict]:
    """Добавить page_end к каждой записи каталога."""
    items = sorted(CATALOG, key=lambda x: x["page"])
    out = []
    for i, item in enumerate(items):
        end = items[i + 1]["page"] - 1 if i + 1 < len(items) else 124
        out.append({**item, "page_end": end})
    return out


def printed_page_to_pdf_index(printed: int) -> int | None:
    """Печатная страница книги → индекс страницы PDF (0-based)."""
    if not POEMS_PDF.is_file():
        return None
    doc = fitz.open(POEMS_PDF)
    for i in range(doc.page_count):
        text = doc[i].get_text()
        if re.search(rf"(?:^|\n)\s*{printed}\s*(?:\n|$)", text):
            return i
    # fallback: печатная 5 ≈ PDF стр. 3 (смещение 2)
    guess = printed + 1
    if 0 <= guess < doc.page_count:
        return guess
    return None
