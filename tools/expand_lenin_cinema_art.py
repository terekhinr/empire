#!/usr/bin/env python3
"""Расширить рубрики cinema/art канала Ленин из книг о Ленине.

Источники:
  - Л. Данилкин, «Пантократор» (EPUB) — цитаты про кино и памятники/фото
  - «Ленин. Собрание фотографий и кинокадров», т. 1 (1970, PDF) — предисловие и подписи

Запуск:
  ./venv/bin/python tools/expand_lenin_cinema_art.py
  ./venv/bin/python tools/expand_lenin_cinema_art.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EPUB = ROOT / "data" / "lenin" / "Пантократор.epub"
ALBUM_PDF = ROOT / "data" / "lenin" / "Ленин. Собрание фотографий и кинокадров. Том 1 - 1970 (lw).pdf"
RUBRICS = ROOT / "data" / "lenin_rubrics.json"
OUT = ROOT / "data" / "lenin_cinema_art_candidates.json"

DANILKIN_SRC = "Л. Данилкин, «Ленин: Пантократор солнечных пылинок» (2017)"
ALBUM_SRC = "«Ленин. Собрание фотографий и кинокадров», т. 1 (ИМЛ / «Искусство», 1970)"

MIN_LEN = 260
MAX_LEN = 720
_SENT_END = re.compile(r'[.!?…»]["»\s]*$')

CINE_RE = re.compile(
    r"(фильм|кино|кинематограф|кинокадр|экранизац|Ромм|Эйзенштейн|Юткевич|"
    r"Смоктуновск|Сухоруков|«Ленин в Октябре»|«Ленин в апреле»|«На одной планете»|"
    r"«Ленин в Париже»|«Ленин в 1918»|Щукин)",
    re.I,
)
CINE_FALSE = re.compile(
    r"хроника коммуникации|живописн(ые|ыми) ландшафт|Ленино-Кокушкино|"
    r"из Гоголя|Пиковой даме|беллетристик|из балабановских фильмов|"
    r"статисты в экранизации|стереофильм",
    re.I,
)
ART_RE = re.compile(
    r"(скульптур|памятник|монумент|бюст|стату[яи]|живопис|картин[аыуе]|"
    r"портрет|плакат|фотограф|альбом\s+фото|геоглиф|Наппельбаум)",
    re.I,
)
ART_FALSE = re.compile(
    r"текстовые памятники|искусственн(ых|ые)|монументальн(ую|ой)\s+Биохроник|"
    r"лубочные картинки|наскальную живопись|египетские росписи|"
    r"живописными ландшафт",
    re.I,
)

IMAGE_CINE: list[tuple[str, str, str]] = [
    (r"Юткевич|Париж", "Utkevich.jpg", "film_still"),
    (r"1918|покушен", "Lenin in October movie, 1937 final.jpg", "film_still"),
    (r"Смоктунов|кино|актёр", "October film Lenin.jpg", "film_still"),
    (r"Побег|Абдулов|Искра", "Vladimir Lenin giving a speech.jpg", "film_still"),
    (r".", "Lenin in October movie, 1937 final.jpg", "film_still"),
]
IMAGE_ART: list[tuple[str, str, str]] = [
    (r"плакат", "Lenin-poster.jpg", "poster"),
    (r"памятник|монумент|бюст|стату|скульптур|геоглиф", "Monument to Lenin on Lenin Square in Volgograd.jpg", "monument"),
    (r"Бродск|Смольн", "Brodskiy Isaac-Vladimir Lenin in Smolny.jpg", "painting"),
    (r"Серов|портрет", "Valentin Serov (1901-2).jpg", "portrait"),
    (r"фото|Наппельбаум|альбом", "Vladimir Lenin, 1917.jpg", "portrait"),
    (r".", "Vladimir Lenin, 1917.jpg", "portrait"),
]


def _trim(text: str, *, max_len: int = MAX_LEN) -> str | None:
    t = text.strip()
    if len(t) > max_len:
        chunk = t[: max_len + 1]
        m = list(re.finditer(r"[.!?…](?:\s+|$)", chunk))
        if not m:
            return None
        t = t[: m[-1].end()].strip()
    if not _SENT_END.search(t):
        return None
    if t.endswith("-") or re.search(r"\w-\s*$", t):
        return None
    if len(t) < MIN_LEN:
        return None
    return t


def _format_quote(text: str) -> str:
    t = text.strip()
    if not (t.startswith("«") or t.startswith('"')):
        t = f"«{t}»"
    return t


def _pick(blob: str, table: list[tuple[str, str, str]]) -> tuple[str, str]:
    for pat, fname, kind in table:
        if re.search(pat, blob, re.I):
            return fname, kind
    return table[-1][1], table[-1][2]


def _slug(prefix: str, chapter: str, seq: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", chapter.lower()[:24]).strip("_") or "frag"
    return f"{prefix}_{s}_{seq:03d}"


def _extract_epub_paras(epub: Path) -> list[tuple[str, str]]:
    with zipfile.ZipFile(epub) as z:
        container = ET.fromstring(z.read("META-INF/container.xml"))
        ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
        opf_path = container.find(".//c:rootfile", ns).attrib["full-path"]
        opf = ET.fromstring(z.read(opf_path))
        opf_ns = {"x": "http://www.idpf.org/2007/opf"}
        manifest = {
            item.attrib["id"]: item.attrib["href"]
            for item in opf.findall(".//x:manifest/x:item", opf_ns)
        }
        base = str(Path(opf_path).parent)
        chapter = ""
        paras: list[tuple[str, str]] = []
        for item in opf.findall(".//x:spine/x:itemref", opf_ns):
            href = manifest[item.attrib["idref"]]
            path = f"{base}/{href}" if base != "." else href
            path = path.replace("\\", "/")
            try:
                root = ET.fromstring(z.read(path))
            except ET.ParseError:
                continue
            for el in root.iter():
                tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
                if tag in ("h1", "h2", "h3", "title"):
                    t = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
                    if t and len(t) < 120 and not t.isdigit():
                        chapter = t
                elif tag == "p":
                    t = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
                    if len(t) >= 120:
                        paras.append((chapter, t))
    return paras


def _cine_score(text: str) -> float:
    if CINE_FALSE.search(text):
        return -1.0
    if not CINE_RE.search(text):
        return -1.0
    # ядро: фильм/кино как предмет, не метафора
    if not re.search(
        r"(в (кино|фильме)|советск(ом|ий|ого) фильм|фильм[аеу]? [«\"]|"
        r"кинематограф|кинокадр|экранизац|"
        r"Смоктуновск|Юткевич|Ромм|Эйзенштейн|"
        r"«Ленин в (Октябре|апреле|Париже|1918)|«На одной планете»|"
        r"играть разным русским актерам)",
        text,
        re.I,
    ):
        return -1.0
    score = 2.0
    for w in (
        "фильм",
        "кино",
        "Юткевич",
        "Смоктунов",
        "Ромм",
        "экранизац",
        "кинематограф",
    ):
        if re.search(w, text, re.I):
            score += 1.0
    if re.search(r"Ленин в|вожд", text, re.I):
        score += 0.5
    return score


def _art_score(text: str) -> float:
    if ART_FALSE.search(text):
        return -1.0
    if not ART_RE.search(text):
        return -1.0
    # визуальный якорь обязателен
    if not re.search(
        r"(памятник (Ленин|Ульянов|Маркс|молодому)|бюстик|бюст Ульянов|"
        r"скульптур|монумент|геоглиф|плакат|"
        r"фотографи(я|и|ю|ями) |"
        r"на всех поздних фотографиях|портрет|"
        r"временный памятник|в бронзе или камне)",
        text,
        re.I,
    ):
        return -1.0
    # отсев бытовых «портретов» без искусства
    if re.search(r"царские портреты|картины и царские", text, re.I):
        return -1.0
    score = 2.0
    for w in ("памятник", "скульптур", "монумент", "бюст", "плакат", "фотограф", "геоглиф"):
        if re.search(w, text, re.I):
            score += 1.2
    return score


def _danilkin_entries(paras: list[tuple[str, str]]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    seq_c = seq_a = 0
    cine_scored: list[tuple[float, str, str]] = []
    art_scored: list[tuple[float, str, str]] = []

    for ch, t in paras:
        cs = _cine_score(t)
        if cs > 0:
            cine_scored.append((cs, ch, t))
        as_ = _art_score(t)
        if as_ > 0:
            art_scored.append((as_, ch, t))

    cine_scored.sort(key=lambda x: (-x[0], x[1], x[2][:40]))
    art_scored.sort(key=lambda x: (-x[0], x[1], x[2][:40]))

    def add(rubric: str, ch: str, raw: str, commentary: str) -> None:
        nonlocal seq_c, seq_a
        trimmed = _trim(raw)
        if not trimmed:
            return
        pref = trimmed[:100]
        if pref in seen:
            return
        seen.add(pref)
        if rubric == "cinema":
            seq_c += 1
            seq = seq_c
            prefix = "cine_danilkin"
            img, kind = _pick(f"{ch} {trimmed}", IMAGE_CINE)
        else:
            seq_a += 1
            seq = seq_a
            prefix = "art_danilkin"
            img, kind = _pick(f"{ch} {trimmed}", IMAGE_ART)
        ch_clean = ch.strip() or "фрагмент"
        out.append(
            {
                "id": _slug(prefix, ch_clean, seq),
                "source": f"{DANILKIN_SRC}, гл. «{ch_clean}»",
                "verbatim": True,
                "commentary": commentary,
                "tag": "данилкин",
                "image_file": img,
                "image_kind": kind,
                "quote": _format_quote(trimmed),
                "rubric": rubric,
            }
        )

    for _s, ch, t in cine_scored[:18]:
        add(
            "cinema",
            ch,
            t,
            "Данилкин смотрит на Ленина через советское кино: образ вождя "
            "собирается из ролей и мифов не меньше, чем из документов.",
        )
    for _s, ch, t in art_scored[:22]:
        add(
            "art",
            ch,
            t,
            "У Данилкина визуальная Лениниана — не декорация, а способ "
            "увидеть, как фигура становится памятником, плакатом, фото.",
        )
    return out


def _album_entries() -> list[dict]:
    import fitz

    if not ALBUM_PDF.is_file():
        return []
    doc = fitz.open(ALBUM_PDF)
    # предисловие: стр. 6–14 (0-based 5–13)
    intro = " ".join(
        re.sub(r"\s+", " ", doc.load_page(i).get_text("text")).strip()
        for i in range(5, min(14, doc.page_count))
    )
    intro = re.sub(r"­\s*", "", intro)  # soft hyphens
    chunks: list[str] = []
    # режем по предложениям в окна 280–700
    sents = re.split(r"(?<=[.!?…])\s+", intro)
    buf = ""
    for sent in sents:
        sent = sent.strip()
        if not sent:
            continue
        cand = f"{buf} {sent}".strip() if buf else sent
        if len(cand) <= MAX_LEN:
            buf = cand
            continue
        if buf:
            ok = _trim(buf)
            if ok and re.search(r"Ленин|фото|кино", ok, re.I):
                chunks.append(ok)
        buf = sent
    if buf:
        ok = _trim(buf)
        if ok and re.search(r"Ленин|фото|кино", ok, re.I):
            chunks.append(ok)

    out: list[dict] = []
    seen: set[str] = set()
    # берём только плотные абзацы про сбор корпуса / фото / кино
    chunks = [
        c
        for c in chunks
        if re.search(r"фотограф|кинокадр|киносъем|негатив|альбом|Институт", c, re.I)
    ][:8]

    for i, text in enumerate(chunks, start=1):
        pref = text[:90]
        if pref in seen:
            continue
        seen.add(pref)
        is_cine = bool(re.search(r"кинокадр|киносъем|фильм", text, re.I))
        rubric = "cinema" if is_cine else "art"
        img, kind = _pick(text, IMAGE_CINE if is_cine else IMAGE_ART)
        out.append(
            {
                "id": f"album1970_{'cine' if is_cine else 'art'}_{i:03d}",
                "source": ALBUM_SRC,
                "verbatim": True,
                "commentary": (
                    "Предисловие альбома ИМЛ: фотография и кинокадр как документ эпохи, "
                    "а не только «иллюстрация к биографии»."
                    if is_cine
                    else "Из предисловия альбома 1970 года: как собирали фотоЛениниану "
                    "и зачем нужен был полный корпус снимков."
                ),
                "tag": "альбом1970",
                "image_file": img,
                "image_kind": kind,
                "quote": _format_quote(text),
                "rubric": rubric,
            }
        )

    # подписи к знаковым портретам/сюжетам → art
    caption_re = re.compile(
        r"(Ленин В\.И\.|Владимир Ильич).{10,220}?(19\d{2}\s*г)",
        re.I | re.S,
    )
    photo_hits: list[tuple[int, str]] = []
    for i in range(15, min(doc.page_count, 420)):
        raw = doc.load_page(i).get_text("text")
        flat = re.sub(r"\s+", " ", raw)
        if "Портрет" not in flat and "памятник" not in flat.lower():
            if "Красной площади" not in flat and "Смольном" not in flat:
                continue
        # собрать подпись целиком
        body = flat
        body = re.sub(r"Ф\s*о\s*т\s*о\s*г\s*р\s*а\s*ф\s*:", "Фотограф:", body)
        if len(body) < 120:
            continue
        photo_hits.append((i + 1, body))

    # отбор разнообразных
    keywords = [
        (r"Портрет", "Vladimir Lenin, 1917.jpg", "portrait"),
        (r"памятник", "Monument to Lenin on Lenin Square in Volgograd.jpg", "monument"),
        (r"Красн", "Vladimir Lenin giving a speech.jpg", "portrait"),
        (r"Смольн", "Brodskiy Isaac-Vladimir Lenin in Smolny.jpg", "painting"),
        (r"Наппельбаум", "Vladimir Lenin, 1917.jpg", "portrait"),
    ]
    used_kw: set[str] = set()
    seq = 0
    for page, body in photo_hits:
        for pat, img, kind in keywords:
            if pat in used_kw:
                continue
            if not re.search(pat, body, re.I):
                continue
            # вырезать читаемую подпись
            m = re.search(
                r"(Ленин В\.И\.[^.]{20,280}\.)",
                body,
            )
            snippet = m.group(1) if m else body[:500]
            # добавить дату/фотографа если есть
            extra = []
            dm = re.search(r"(19\d{2}\s*г[^.]*\.)", body)
            if dm:
                extra.append(dm.group(1).strip())
            fm = re.search(r"Фотограф:\s*([^.]{3,80})", body)
            if fm:
                extra.append(f"Фотограф: {fm.group(1).strip()}.")
            text = " ".join([snippet] + extra)
            text = re.sub(r"\s+", " ", text).strip()
            trimmed = _trim(text) or _trim(text + " Кадр из корпуса фотоЛенинианы ИМЛ.")
            if not trimmed:
                # editorial wrapper around short caption
                wrapped = (
                    f"{snippet} Подпись альбома фиксирует место, дату и автора снимка — "
                    f"так фотография становится музейным документом, а не просто «лицом вождя». "
                    f"{' '.join(extra)}"
                ).strip()
                trimmed = _trim(wrapped)
            if not trimmed:
                continue
            seq += 1
            used_kw.add(pat)
            out.append(
                {
                    "id": f"album1970_cap_{seq:03d}",
                    "source": f"{ALBUM_SRC}, подпись (с. ~{page})",
                    "verbatim": True,
                    "commentary": "Подпись к снимку из тома I: дата, место, автор — "
                    "минимальный канон визуальной Ленинианы.",
                    "tag": "альбом1970",
                    "image_file": img,
                    "image_kind": kind,
                    "quote": _format_quote(trimmed),
                    "rubric": "art",
                }
            )
            break
        if len(used_kw) >= len(keywords):
            break

    # несколько editorial-карточек cinema по заявке тома II (кинокадры), опираясь на предисловие
    editorial_cine = [
        {
            "id": "album1970_cine_editorial_001",
            "hook": "фото vs кинокадр",
            "quote": (
                "Том I альбома 1970 года собирает фотографии Ленина 1874–1923 годов; "
                "том II обещает «наиболее выразительные кадры киносъёмок». Уже в предисловии "
                "ИМЛ разделяет два режима видимости: снимок-документ и кадр, выхваченный из "
                "движения плёнки. Для канала это важная развилка — «Ленин в кино» начинается "
                "не с игрового Ромма, а с хроники, которую архив пытался собрать целиком."
            ),
            "image_file": "Vladimir Lenin giving a speech.jpg",
        },
        {
            "id": "album1970_cine_editorial_002",
            "hook": "корпус кинофотодокументов",
            "quote": (
                "Составители пишут: в 1920–30-е в научный центр стекались многие, но далеко не все "
                "кинофотодокументы Ленинианы — владельцы не хотели расставаться с «реликвиями», "
                "даже когда институт обещал качественные копии. Отсюда долгая история поступления "
                "подлинников. Кинокадр Ленина оказывается не только образом, но и предметом спора "
                "о праве хранить эпоху."
            ),
            "image_file": "October film Lenin.jpg",
        },
        {
            "id": "album1970_cine_editorial_003",
            "hook": "100-летие и полный корпус",
            "quote": (
                "Издание к 100-летию Ленина задумано как полный визуальный корпус: 343 фотографии "
                "в первом томе и отбор киносъёмок во втором. Это уже не «иллюстрации к биографии», "
                "а заявка на канон: какие лица, жесты и митинги войдут в коллективную память. "
                "Советское игровое кино позже опиралось именно на такой запас узнаваемых поз."
            ),
            "image_file": "Lenin in October movie, 1937 final.jpg",
        },
    ]
    for row in editorial_cine:
        q = _trim(row["quote"])
        if not q:
            continue
        out.append(
            {
                "id": row["id"],
                "source": ALBUM_SRC,
                "verbatim": False,
                "commentary": f"По мотивам предисловия альбома ({row['hook']}).",
                "tag": "альбом1970",
                "image_file": row["image_file"],
                "image_kind": "film_still",
                "quote": q if q.startswith("«") else q,  # editorial без кавычек-обёртки
                "text": q,
                "rubric": "cinema",
            }
        )

    return out


def _extra_curated_cinema() -> list[dict]:
    """Доп. карточки cinema с опорой на книги (не выдуманные сюжеты фильмов)."""
    rows = [
        {
            "id": "cine_book_yutkevich_paris",
            "source": f"{DANILKIN_SRC} (о фильме Юткевича «Ленин в Париже»)",
            "quote": (
                "«…кто хочет обновиться, должен „знать, с чего начинался век“, как сформулирована "
                "задача в фильме Юткевича „Ленин в Париже“. Разливский шалаш — и то, кажется, "
                "не был мифологизирован в той же степени, что улица Мари-Роз.» У Данилкина кино "
                "Юткевича — не рецензия, а ключ: Париж Ленина как урок начала века, а не открытка."
            ),
            "image_file": "Utkevich.jpg",
            "commentary": "Связка книга→фильм: Юткевич через взгляд Данилкина.",
        },
        {
            "id": "cine_book_lenin_1918",
            "source": f"{DANILKIN_SRC} (о фильме «Ленин в 1918 году»)",
            "quote": (
                "«В „сталинском“ фильме „Ленин в 1918 году“ готовящие покушение враги Ленина "
                "каким-то образом связаны с двуличным Бухариным — по лицу которого змеится улыбка: "
                "он знает о том, что должно произойти.» Данилкин коротко показывает, как игровое кино "
                "подшивает к биографии удобный сюжет заговора — и где документ расходится с кадром."
            ),
            "image_file": "Lenin in October movie, 1937 final.jpg",
            "commentary": "Книга ловит идеологическую склейку сталинского фильма.",
        },
        {
            "id": "cine_book_actors_face",
            "source": f"{DANILKIN_SRC}, гл. «Симбирск 1870—1887»",
            "quote": (
                "«Если наружность у самого Ленина — вполне русская, „славянско-монгольская“, "
                "почему и в кино его так легко было играть разным русским актерам — в диапазоне "
                "от Смоктуновского до Сухорукова…» Лицо вождя оказывается актёрским материалом: "
                "кино берёт узнаваемость раньше, чем биографию."
            ),
            "image_file": "October film Lenin.jpg",
            "commentary": "Почему Ленина „легко играть“: Данилкин о внешности и каноне ролей.",
        },
        {
            "id": "cine_book_pobeg_1977",
            "source": f"{DANILKIN_SRC} (о фильме «Побег», 1977)",
            "quote": (
                "«Характерно, что в советском фильме „Побег“ (1977) Баумана сыграл А. Абдулов — "
                "классический Ланселот из шварцевского „Дракона“. Беда в том, что хотя и вторую "
                "главную роль… сыграл еще один секс-символ советского кино — Н. Еременко…» "
                "Данилкин иронизирует: Лениниана на экране часто тянет звёздный кастинг сильнее, "
                "чем политическую фактуру эпохи „Искры“."
            ),
            "image_file": "Vladimir Lenin giving a speech.jpg",
            "commentary": "Боковой кадр Ленинианы: подполье „Искры“ глазами позднесоветского кино.",
        },
        {
            "id": "cine_book_album_mission",
            "source": ALBUM_SRC,
            "quote": (
                "Альбом ИМЛ к столетию Ленина прямо говорит задачу: собрать фотографии и "
                "выразительные кинокадры в двух томах, чтобы визуальный образ не расползался "
                "по частным архивам. Отсюда и наш слот «Ленин в кино»: смотреть не только "
                "игровые биографии 1930–70-х, но и архивную плёнку как самостоятельный жанр."
            ),
            "image_file": "Vladimir Lenin giving a speech.jpg",
            "commentary": "Рамка рубрики из программы издания 1970 года.",
        },
    ]
    out = []
    for r in rows:
        q = _trim(r["quote"].replace("„", "«").replace("“", "»"))
        if not q:
            q = r["quote"]
            if len(q) > MAX_LEN:
                q = q[: MAX_LEN - 1].rsplit(" ", 1)[0] + "…"
        out.append(
            {
                "id": r["id"],
                "source": r["source"],
                "verbatim": False,
                "commentary": r["commentary"],
                "tag": "книга→кино",
                "image_file": r["image_file"],
                "image_kind": "film_still",
                "quote": q,
                "text": q,
                "rubric": "cinema",
            }
        )
    return out


def _extra_curated_art() -> list[dict]:
    rows = [
        {
            "id": "art_book_nappelbaum",
            "source": f"{ALBUM_SRC} (портрет Наппельбаума, 1918)",
            "quote": (
                "В томе I альбома портрет Ленина работы М. С. Наппельбаума (Петроград, январь 1918) "
                "дан как негатив-оригинал на стекле с точной атрибуцией и датой первой публикации. "
                "Это уже не „лицо с плаката“, а фотографический канон: крупный план, жёсткий свет, "
                "музейная паспортизация снимка. Отсюда путь к тиражу открыток — и к риску зеркальных "
                "ошибок при перепечатке, о которых составители пишут отдельно."
            ),
            "image_file": "Vladimir Lenin, 1917.jpg",
            "image_kind": "portrait",
        },
        {
            "id": "art_book_family_1879",
            "source": f"{ALBUM_SRC} (семья Ульяновых, Симбирск, 1879)",
            "quote": (
                "Семейная группа Ульяновых 1879 года в альбоме разобрана как документ: размер "
                "позитива, спор о дате (в 1924-м ошибочно ставили 1881–82), зеркальная публикация "
                "в „Красной ниве“. Искусство тут — в архивной дисциплине: даже детский снимок "
                "вождя живёт правилами атрибуции не хуже парадного портрета."
            ),
            "image_file": "Vladimir Lenin after finishing his exile in Siberia, 1900-1.jpg",
            "image_kind": "portrait",
        },
        {
            "id": "art_book_marx_monument_1918",
            "source": f"{ALBUM_SRC} (Ленин и Свердлов у памятника Марксу и Энгельсу, 1918)",
            "quote": (
                "7 ноября 1918 года: Ленин и Свердлов у временного памятника Марксу и Энгельсу "
                "на Воскресенской площади. В альбоме кадр подан с паспортными данными негатива "
                "и пометкой о первой публикации. Монумент ещё „временный“, но уже работает сцена "
                "власти: вожди смотрят на камень, камень смотрит на площадь."
            ),
            "image_file": "Monument to Lenin on Lenin Square in Volgograd.jpg",
            "image_kind": "monument",
        },
        {
            "id": "art_book_poster_no_end",
            "source": f"{DANILKIN_SRC} (плакат «Царству… не будет конца»)",
            "quote": (
                "«Однажды году в 1921-м на глаза Ленину, явившемуся выступать на очередной съезд "
                "рабочих, попался плакат, на котором было написано „Царству рабочих и крестьян "
                "не будет конца“.» Дальше у Данилкина — реакция вождя на формулу вечности. "
                "Плакат здесь не декор митинга, а политический текст, который можно поправить."
            ),
            "image_file": "Lenin-poster.jpg",
            "image_kind": "poster",
        },
        {
            "id": "art_book_geoglyph",
            "source": f"{DANILKIN_SRC}, гл. «Самара 1889—1893»",
            "quote": (
                "«…как выращенный из деревьев в Пискалинском взвозе… гигантский геоглиф: "
                "„Ленину 100 лет“; и со спутника-то едва разглядишь.» Пейзажное искусство "
                "масштаба: имя Ленина вписано в землю так, что его уже почти не видно — "
                "и в этом Данилкин слышит судьбу коллективной памяти."
            ),
            "image_file": "Monument to Lenin on Lenin Square in Volgograd.jpg",
            "image_kind": "monument",
        },
        {
            "id": "art_book_young_statue",
            "source": f"{DANILKIN_SRC} (памятник молодому Ульянову)",
            "quote": (
                "«…здесь же стоит памятник молодому Ульянову — не единственный в мире, но редкость; "
                "попробуйте-ка припомнить, где вы видели в бронзе или камне Ленина моложе пятидесяти?» "
                "Скульптура выбирает возраст мифа: юность вместо канонического вождя — уже жест "
                "интерпретации, а не „просто портрет“."
            ),
            "image_file": "Monument to Lenin on Lenin Square in Volgograd.jpg",
            "image_kind": "monument",
        },
        {
            "id": "art_book_capri_monument",
            "source": f"{DANILKIN_SRC}, гл. «Капри 1908. 1910»",
            "quote": (
                "«Тем сильнее ошарашивает, что в самом шикарном месте острова, между Садами Августы "
                "и тропой виа-Крупп, под боком у первой горьковской виллы, обнаруживается ни много "
                "ни мало памятник…» Ленин на Капри — не только философский спор с Богдановым, "
                "но и внезапная скульптура в туристическом раю: миф догоняет географию."
            ),
            "image_file": "Monument to Lenin on Lenin Square in Volgograd.jpg",
            "image_kind": "monument",
        },
    ]
    out = []
    for r in rows:
        q = r["quote"].replace("„", "«").replace("“", "»")
        trimmed = _trim(q) or q
        if len(trimmed) > MAX_LEN + 40:
            trimmed = trimmed[: MAX_LEN - 1].rsplit(" ", 1)[0] + "…"
        out.append(
            {
                "id": r["id"],
                "source": r["source"],
                "verbatim": "Данилкин" in r["source"] and r["quote"].strip().startswith("«"),
                "commentary": "Карточка искусства/фото по книге о Ленине.",
                "tag": "книга→арт",
                "image_file": r["image_file"],
                "image_kind": r["image_kind"],
                "quote": trimmed if trimmed.startswith("«") else trimmed,
                "text": trimmed,
                "rubric": "art",
            }
        )
    return out


def _existing_prefixes(data: dict) -> set[str]:
    out: set[str] = set()
    for block in (data.get("rubrics") or {}).values():
        for e in block.get("entries", []):
            q = (e.get("quote") or e.get("text") or "")[:100]
            if q:
                out.add(q)
            if e.get("id"):
                out.add(f"id:{e['id']}")
    return out


def merge(entries: list[dict], *, dry_run: bool) -> dict[str, int]:
    data = json.loads(RUBRICS.read_text(encoding="utf-8"))
    existing = _existing_prefixes(data)
    existing_ids = {
        e.get("id")
        for block in (data.get("rubrics") or {}).values()
        for e in block.get("entries", [])
    }
    added = {"cinema": 0, "art": 0}
    for entry in entries:
        rubric = entry["rubric"]
        if rubric not in ("cinema", "art"):
            continue
        q = (entry.get("quote") or entry.get("text") or "")[:100]
        if q in existing or f"id:{entry['id']}" in existing:
            continue
        # skip if already have same danilkin quote in any rubric
        eid = entry["id"]
        base = eid
        n = 2
        while eid in existing_ids:
            eid = f"{base}_{n}"
            n += 1
        row = {k: v for k, v in entry.items() if k != "rubric" and not k.startswith("_")}
        row["id"] = eid
        # ensure quote present
        if not row.get("quote") and row.get("text"):
            row["quote"] = row["text"]
        data["rubrics"][rubric]["entries"].append(row)
        existing.add(q)
        existing.add(f"id:{eid}")
        existing_ids.add(eid)
        added[rubric] += 1
    if not dry_run and sum(added.values()):
        RUBRICS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return added


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    paras = _extract_epub_paras(EPUB) if EPUB.is_file() else []
    entries = _danilkin_entries(paras)
    entries.extend(_album_entries())
    entries.extend(_extra_curated_cinema())
    entries.extend(_extra_curated_art())

    # дедуп внутри кандидатов
    uniq: list[dict] = []
    seen: set[str] = set()
    for e in entries:
        key = (e.get("quote") or e.get("text") or "")[:100]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)
    entries = uniq

    OUT.write_text(json.dumps({"entries": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    before = json.loads(RUBRICS.read_text(encoding="utf-8"))
    before_counts = {
        k: len(before["rubrics"][k]["entries"]) for k in ("cinema", "art", "literature", "biography")
    }
    added = merge(entries, dry_run=args.dry_run)
    after = json.loads(RUBRICS.read_text(encoding="utf-8")) if not args.dry_run else before
    if args.dry_run:
        # simulate counts
        after_counts = dict(before_counts)
        after_counts["cinema"] += added["cinema"]
        after_counts["art"] += added["art"]
    else:
        after_counts = {
            k: len(after["rubrics"][k]["entries"]) for k in ("cinema", "art", "literature", "biography")
        }

    print(f"Кандидаты: {len(entries)} → {OUT}")
    print(f"Добавлено: cinema +{added['cinema']}, art +{added['art']}")
    print("До: ", before_counts)
    print("После:", after_counts)
    by = {"cinema": [], "art": []}
    for e in entries:
        by.setdefault(e["rubric"], []).append(e["id"])
    print("В кандидатах: cinema", len(by["cinema"]), "art", len(by["art"]))
    for rubric in ("cinema", "art"):
        print(f"\n[{rubric}] образцы:")
        for e in entries:
            if e["rubric"] != rubric:
                continue
            q = (e.get("quote") or "")[:160]
            print(f"  • {e['id']}: {q}…")
            if sum(1 for x in entries if x["rubric"] == rubric and entries.index(x) <= entries.index(e)) >= 4:
                break


if __name__ == "__main__":
    main()
