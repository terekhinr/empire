#!/usr/bin/env python3
"""Парсит batch-посты «Классическая баня» из markdown и пишет gdepar_classic_banya.json."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_FILES = [
    ROOT / "data" / "gdepar_classic_banya_import_raw.md",
    ROOT / "data" / "gdepar_classic_banya_import_raw_61_160.md",
]
OUT = ROOT / "data" / "gdepar_classic_banya.json"

# Wikimedia Commons — image_file для prefetch
AUTHOR_PORTRAITS: dict[str, str] = {
    "Ф.М. Достоевский": "Vasily Perov - Портрет Ф.М.Достоевского - Google Art Project.jpg",
    "В.А. Гиляровский": "Vladimir Gilyarovsky by Sergey Malyutin.jpg",
    "В.М. Шукшин": "Shukshin.jpg",
    "М.М. Зощенко": "Zoshchenko 1938.jpg",
    "Н.В. Гоголь": "Iwan Nikolajewitsch Kramskoj 002.jpg",
    "М. Горький": "Maxim Gorky 1930.jpg",
    "А.И. Куприн": "Aleksandr Ivanovich Kuprin.jpg",
    "А.Н. Островский": "Alexander Nikolayevich Ostrovsky 3.jpg",
    "М.Е. Салтыков-Щедрин": "Mikhail Evgrafovich Saltykov-Shchedrin, head-and-shoulders portrait, facing left LCCN99615562.jpg",
    "В.П. Астафьев": "Victor Astafiev 1989.jpg",
    "И.А. Гончаров": "Ivan Goncharov.jpg",
    "И.А. Бунин": "Ivan Bunin 1933.jpg",
    "И. Ильф и Е. Петров": "Ilf and Petrov.jpg",
    "А.С. Пушкин": "Kiprensky Pushkin.jpg",
    "Ф.А. Абрамов": "Fyodor Abramov.jpg",
    "М.А. Булгаков": "Mikhail Bulgakov, 1923.jpg",
    "Л.Н. Толстой": "L.N.Tolstoy Prokudin-Gorsky.jpg",
    "М.А. Шолохов": "Михаил Александрович Шолохов.jpg",
    "К.Г. Паустовский": "Konstantin Paustovsky 1967.jpg",
    "А.П. Чехов": "Anton Chekhov 1889.jpg",
    "Д.Н. Мамин-Сибиряк": "Dmitry Mamin-Sibiryak.jpg",
    "А.П. Платонов": "Andrey Platonov.jpg",
    "В.Г. Распутин": "Valentin Rasputin.jpg",
    "Ф.К. Сологуб": "Fyodor Sologub.jpg",
    "Н.С. Лесков": "Leskov - portrait of author.jpg",
    "В.В. Набоков": "Vladimir Nabokov, Van Vechten portrait, May 25, 1951.jpg",
    "И.С. Тургенев": "Turgenev 1879 by Dmitriev-Orenburgsky.jpg",
    "Ю.В. Трифонов": "Yury Trifonov.jpg",
    "П.П. Бажов": "Pavel Bazhov.jpg",
    "С.Д. Довлатов": "Sergei Dovlatov.jpg",
    "А.А. Фет": "Afanasy Fet by Levitsky.jpg",
    "В.И. Белов": "Vasily Belov.jpg",
    "А.Т. Твардовский": "Aleksandr Tvardovsky.jpg",
    "А.Н. Толстой": "Aleksey Nikolayevich Tolstoy.jpg",
    "В.А. Солоухин": "Vladimir Soloukhin.jpg",
    "Б.Л. Пастернак": "Boris Pasternak 1959.jpg",
    "В.С. Высоцкий": "Vladimir Vysotsky 1979.jpg",
    "А.С. Грибоедов": "Alexander Griboyedov.jpg",
    "В.Я. Шишков": "Vladimir Shishkov.jpg",
    "И.С. Шмелев": "Ivan Shmelev.jpg",
    "М.М. Пришвин": "Mikhail Prishvin.jpg",
    "В.А. Каверин": "Veniamin Kaverin.jpg",
    "В.П. Аксенов": "Vassily Aksyonov.jpg",
    "В.М. Гаршин": "Vsevolod Garshin.jpg",
    "В.В. Вересаев": "Vikenty Veresaev.jpg",
    "Л.Н. Андреев": "Leonid Andreyev.jpg",
    "А.А. Фадеев": "Aleksandr Fadeev.jpg",
    "А.С. Грин": "Aleksandr Green.jpg",
    "Б.С. Житков": "Boris Zhitkov.jpg",
    "С.А. Есенин": "Sergei Yesenin 1922.jpg",
    "А.И. Герцен": "Herzen ge.jpg",
    "А.Т. Аверченко": "Arkady Averchenko.jpg",
    "Б.А. Можаев": "Boris Mozhaev.jpg",
    "В.И. Даль": "Vladimir Dal.jpg",
    "В.А. Жуковский": "Vasily Zhukovsky.jpg",
    "Н.Г. Помяловский": "Nikolay Pomyalovsky.jpg",
    "А.А. Блок": "Alexander Blok.jpg",
    "В.В. Маяковский": "Vladimir Mayakovsky.jpg",
    "Ю.К. Олеша": "Yury Olesha.jpg",
    "С.Т. Аксаков": "Portrait of Sergey Aksakov by Kramskoy.jpg",
    "А.К. Толстой": "Aleksey Konstantinovich Tolstoy.jpg",
    "М.И. Цветаева": "Marina Tsvetaeva.jpg",
    "Г.И. Успенский": "1884 Yaroshenko Portrait Schriftsteller G.I. Uspenskoje anagoria.JPG",
    "Н.А. Некрасов": "Nikolay Nekrasov by Ge.jpg",
    "А.А. Фадеев": "Aleksandr Fadeev 1950.jpg",
    "Б.А. Можаев": "Boris Mozhaev.jpg",
    "В.М. Гаршин": "Vsevolod Garshin.jpg",
    "А.К. Толстой": "Aleksey Konstantinovich Tolstoy.jpg",
    "В.Т. Шаламов": "Varlam Shalamov.jpg",
}

TAG_BY_AUTHOR: dict[str, str] = {
    "И. Ильф и Е. Петров": "ильф_петров",
    "М. Горький": "горький",
}

WORK_FIX: dict[str, str] = {
    "«Записок из Мёртвого дома»": "«Записки из Мёртвого дома»",
    "«Записок из Мертвого дома»": "«Записки из Мёртвого дома»",
    "«Записок охотника»": "«Записки охотника»",
    "«Вечеров на хуторе близ Диканьки»": "«Вечера на хуторе близ Диканьки»",
    "«Скрипки Ротшильда»": "«Скрипка Ротшильда»",
}


def slugify(s: str) -> str:
    s = s.lower().strip()
    tr = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    out = []
    for ch in s:
        if ch in tr:
            out.append(tr[ch])
        elif ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("_")
    slug = re.sub(r"_+", "_", "".join(out)).strip("_")
    return slug[:48] or "post"


def author_tag(author: str) -> str:
    if author in TAG_BY_AUTHOR:
        return TAG_BY_AUTHOR[author]
    surname = author.split()[-1].lower()
    return re.sub(r"[^а-яё\-]", "", surname)[:24] or "классика"


def extract_work(quote: str, header: str) -> str:
    patterns = [
        r"\(из\s+[«\"]([^»\"]+)[»\"]",
        r"\(из\s+рассказа\s+[«\"]([^»\"]+)[»\"]",
        r"\(из\s+повести\s+[«\"]([^»\"]+)[»\"]",
        r"\(из\s+романа\s+[«\"]([^»\"]+)[»\"]",
        r"\(из\s+пьес[^»\"]*[«\"]([^»\"]+)[»\"]",
    ]
    for pat in patterns:
        m = re.search(pat, quote, re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            return f"«{title}»" if not title.startswith("«") else title
    # fallback: тема из заголовка
    if "—" in header:
        theme = header.split("—", 1)[1].strip()
        return f"({theme})"
    return "(классическая проза)"


def clean_quote(raw: str) -> str:
    q = raw.strip()
    q = re.sub(r"^«\s*", "«", q)
    # убрать хвостовую атрибуцию
    q = re.sub(
        r"\s*\((?:из|стилизация|контекст|адаптация)[^)]*\)\s*$",
        "",
        q,
        flags=re.IGNORECASE,
    ).strip()
    return q


def short_text(quote: str, limit: int = 320) -> str:
    q = quote.strip()
    if len(q) <= limit:
        return q
    cut = q[:limit]
    dot = cut.rfind(".")
    if dot > 120:
        return cut[: dot + 1].strip()
    return cut.rstrip() + "…"


def parse_posts(text: str) -> list[dict]:
    blocks = re.split(r"(?=Пост №\d+[:：])", text)
    entries: list[dict] = []
    seen_ids: set[str] = set()

    for block in blocks:
        if not block.strip() or "Цитата" not in block:
            continue
        m_hdr = re.match(r"Пост №(\d+)[:：]\s*(.+?)(?:\n|$)", block.strip())
        if not m_hdr:
            continue
        num, header = m_hdr.group(1), m_hdr.group(2).strip()
        if "—" in header:
            author, _theme = [p.strip() for p in header.split("—", 1)]
        else:
            author, _theme = header, ""

        quote_m = re.search(
            r"Цитата:\s*\n+(.*?)(?:\n+Критика:|\n+Промт для изображения:|\Z)",
            block,
            re.DOTALL,
        )
        note_m = re.search(
            r"Критика:\s*\n+(.*?)(?:\n+Промт для изображения:|\n+Пост №|\Z)",
            block,
            re.DOTALL,
        )
        if not quote_m or not note_m:
            print(f"skip post {num}: missing quote or note")
            continue

        quote = clean_quote(quote_m.group(1).strip())
        note = note_m.group(1).strip()
        work = extract_work(quote_m.group(1), header)
        work = WORK_FIX.get(work, work)

        base_id = f"{slugify(author)}_{slugify(_theme.split()[0] if _theme else str(num))}"
        eid = base_id
        n = 2
        while eid in seen_ids:
            eid = f"{base_id}_{n}"
            n += 1
        seen_ids.add(eid)

        image_file = AUTHOR_PORTRAITS.get(author)
        entry: dict = {
            "id": eid,
            "author": author,
            "work": work,
            "text": short_text(quote),
            "quote": quote,
            "note": note,
            "tag": author_tag(author),
            "image_kind": "author_portrait",
        }
        if image_file:
            entry["image_file"] = image_file
        entries.append(entry)

    return entries


def load_source_text() -> str:
    parts: list[str] = []
    for path in SRC_FILES:
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def main() -> int:
    text = load_source_text()
    if not text.strip():
        print("Missing import source files")
        return 1
    entries = parse_posts(text)
    out = {
        "_comment": (
            "Рубрика «Классическая баня» — цитаты и разбор из русской литературы. "
            "note = блок «О чём писал автор» в посте. image_file — Wikimedia Commons."
        ),
        "entries": entries,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} entries -> {OUT}")
    return 0 if entries else 1


if __name__ == "__main__":
    raise SystemExit(main())
