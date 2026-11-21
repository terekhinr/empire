"""Детерминированные правки из разбора 400 реальных предложений (gold/FINDINGS.md).

pre_normalize()  — до ru-normalizr: числа/века/списки/аббревиатуры, которые он читает неверно.
post_normalize() — после ru-normalizr: откат его известных искажений.
post_stress()    — после silero-stress: все/всё, «в … году».
"""
from __future__ import annotations

import re

_W = "A-Za-zА-Яа-яЁё"

_MORPH = None
_MORPH_TRIED = False


def _morph():
    global _MORPH, _MORPH_TRIED
    if not _MORPH_TRIED:
        _MORPH_TRIED = True
        try:
            import pymorphy3

            _MORPH = pymorphy3.MorphAnalyzer()
        except Exception:
            _MORPH = None
    return _MORPH


def _n2w(n: int, *, ordinal: bool = False) -> str | None:
    try:
        from num2words import num2words

        return num2words(n, lang="ru", to="ordinal") if ordinal else num2words(n, lang="ru")
    except Exception:
        return None


def _inflect_last(phrase: str, tags: set[str]) -> str:
    m = _morph()
    if m is None or not tags:
        return phrase
    words = phrase.split()
    for p in m.parse(words[-1]):
        if "ADJF" in p.tag or "NUMR" in p.tag:
            inf = p.inflect(tags)
            if inf:
                words[-1] = inf.word
                break
    return " ".join(words)


def _noun_tags(noun: str) -> set[str]:
    """Род/падеж/число существительного (ед.ч. в приоритете: «века» = род.п. ед.)."""
    m = _morph()
    if m is None:
        return set()
    parses = [p for p in m.parse(noun) if "NOUN" in p.tag]
    if not parses:
        return set()
    sing = [p for p in parses if "sing" in p.tag]
    p = (sing or parses)[0]
    tags = {x for x in (p.tag.gender, p.tag.case, p.tag.number) if x}
    if "plur" in tags:
        tags = {x for x in tags if x not in ("masc", "femn", "neut")}
    return tags


# ---------------------------------------------------------------- pre-normalize

_ROMAN_VALS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _roman_to_int(s: str) -> int | None:
    s = s.upper().replace("Х", "X")  # кириллическая Х в «ХХ век»
    if not s or not re.fullmatch(r"[IVXLC]+", s):
        return None
    total, prev = 0, 0
    for ch in reversed(s):
        v = _ROMAN_VALS[ch]
        total += -v if v < prev else v
        prev = v
    return total if 0 < total < 200 else None


# число/римское + существительное, требующее порядкового: «21 века», «XX столетия», «13 статью»
_ORD_NOUNS = r"(?:век|века|веку|веке|веком|столети[еяюи]|столетием|стать[яиюёе]|статьей|статьёй)"
_ORD_RE = re.compile(
    rf"(?<![{_W}\d.,])(\d{{1,2}}|[IVXLХ]{{1,6}})(?:-?(?:й|го|м|ом|ый|ой))?\s+({_ORD_NOUNS})(?![{_W}])",
    re.IGNORECASE,
)


def _ordinal_noun(m: re.Match[str]) -> str:
    raw, noun = m.group(1), m.group(2)
    n = int(raw) if raw.isdigit() else _roman_to_int(raw)
    if n is None:
        return m.group(0)
    if not raw.isdigit() and not re.fullmatch(r"[IVXLХ]+", raw):
        return m.group(0)
    tags = _noun_tags(noun.lower())
    if raw.isdigit() and "gent" in tags and "sing" in tags and n % 10 in (2, 3, 4) and not 12 <= n % 100 <= 14:
        # «2 века», «3 статьи» — может быть количественным. Порядковое только с подсказкой.
        prev = re.findall(rf"[{_W}]+", m.string[max(0, m.start() - 30):m.start()])
        cue = prev[-1].lower() if prev else ""
        if cue not in {"с", "до", "от", "из", "начала", "середины", "конца", "рубежа", "половины",
                       "годов", "годах", "середине", "начале", "конце", "течение"}:
            return m.group(0)
    word = _n2w(n, ordinal=True)
    if not word:
        return m.group(0)
    return f"{_inflect_last(word, tags)} {noun}"


_LIST_ORD = {
    1: "во-первых", 2: "во-вторых", 3: "в-третьих", 4: "в-четвёртых", 5: "в-пятых",
    6: "в-шестых", 7: "в-седьмых", 8: "в-восьмых", 9: "в-девятых", 10: "в-десятых",
}


def _letnij(m: re.Match[str]) -> str:
    """30-летним → тридцатилетним; 100-летний → столетний."""
    n, tail = int(m.group(1)), m.group(2)
    special = {1: "одно", 100: "сто", 1000: "тысяче", 40: "сорока", 90: "девяноста"}
    if n in special:
        return special[n] + tail
    words = (_n2w(n) or "").split()
    mo = _morph()
    if not words or mo is None:
        return m.group(0)
    out = []
    for w in words:
        if w == "сорок":
            out.append("сорока")
            continue
        if w == "девяносто":
            out.append("девяноста")
            continue
        if w == "сто":
            out.append("сто")
            continue
        p = mo.parse(w)[0]
        inf = p.inflect({"gent"})
        out.append(inf.word if inf else w)
    return "".join(out) + tail


_ABBR_SPOKEN = [
    (r"\bБПЛА\b", "бэ пэ эл а"),
    (r"\bДНР\b", "дэ эн эр"),
    (r"\bЛНР\b", "эл эн эр"),
    (r"\bЛГБТ\b", "эл гэ бэ тэ"),
    (r"\bКСИР\b", "ксир"),
    (r"\bООН\b", "оон"),
    (r"\bЕР\b", "е эр"),
]


def _num_gent(n: int) -> str:
    """57 → «пятидесяти семи» (род.п. всех частей количественного)."""
    words = (_n2w(n) or str(n)).split()
    mo = _morph()
    if mo is None:
        return " ".join(words)
    out = []
    for w in words:
        inf = None
        for p in mo.parse(w):
            if "NUMR" in p.tag or p.normal_form in ("тысяча", "миллион", "миллиард"):
                inf = p.inflect({"gent"})
                break
        out.append(inf.word if inf else w)
    return " ".join(out)


def _year_ord(year: int, case: str) -> str:
    w = _n2w(year, ordinal=True) or str(year)
    return _inflect_last(w, {case}) if case != "nomn" else w


def _years_range(m: re.Match[str]) -> str:
    prep, a, b = (m.group(1) or ""), int(m.group(2)), int(m.group(3))
    if not (1000 <= a <= 2100 and 1000 <= b <= 2100):
        return m.group(0)
    p = prep.strip().lower()
    if p == "с":
        return f"с {_year_ord(a, 'gent')} по {_year_ord(b, 'accs')}"
    if p == "в":
        return f"в {_year_ord(a, 'loct')} — {_year_ord(b, 'loct')}"
    return f"{prep}{_year_ord(a, 'nomn')} — {_year_ord(b, 'nomn')}"


_MONTH_ABBR = {
    "янв": "января", "фев": "февраля", "февр": "февраля", "мар": "марта", "апр": "апреля",
    "мая": "мая", "июн": "июня", "июл": "июля", "авг": "августа", "сен": "сентября",
    "сент": "сентября", "окт": "октября", "ноя": "ноября", "нояб": "ноября", "дек": "декабря",
}
_MONTH_ABBR_RE = "|".join(sorted(_MONTH_ABBR, key=len, reverse=True))


def _dates(text: str) -> str:
    """«09 нояб» в начале строки (дата-заголовок) → «девятое ноября»; внутри фразы — только месяц."""

    def _head(m: re.Match[str]) -> str:
        day = int(m.group(2))
        if not 1 <= day <= 31:
            return m.group(0)
        word = _n2w(day, ordinal=True) or m.group(2)
        word = _inflect_last(word, {"neut", "nomn", "sing"})
        return f"{m.group(1)}{word} {_MONTH_ABBR[m.group(3).lower()]}"

    text = re.sub(
        rf"(?im)^(\s*#*\s*)(\d{{1,2}})\s+({_MONTH_ABBR_RE})\.?(?![А-Яа-яЁё])",
        _head,
        text,
    )
    return re.sub(
        rf"(?i)(?<=\d\s)({_MONTH_ABBR_RE})\.?(?![А-Яа-яЁё])",
        lambda m: _MONTH_ABBR[m.group(1).lower()],
        text,
    )


def pre_normalize(text: str) -> str:
    text = _dates(text)
    # «45+», «300+» — иначе висящий «+» уходит в разметку SpeechKit
    text = re.sub(r"(\d)\+(?=[\s.,;:!?)\]»\"]|$)", r"\1 плюс", text)
    # списки «1)», «2)» → во-первых, во-вторых
    text = re.sub(
        r"(?:(?<=^)|(?<=[\s(:;]))(\d{1,2})\)\s+",
        lambda m: f"{_LIST_ORD[int(m.group(1))]}, " if int(m.group(1)) in _LIST_ORD else m.group(0),
        text,
    )
    # века / столетия / статьи — порядковые с согласованием
    text = _ORD_RE.sub(_ordinal_noun, text)
    # «30-летним» → «тридцатилетним»
    text = re.sub(r"(?<![\d.,])(\d{1,3})-(летн\w*|лети\w*)", _letnij, text)
    # «в далёком 2020-м» → предложный порядковый
    text = re.sub(
        r"(?i)(\bв\s+(?:[а-яё]+\s+)?)(\d{4})-м\b",
        lambda m: f"{m.group(1)}{_year_ord(int(m.group(2)), 'loct')}",
        text,
    )
    # диапазоны лет «с 2023–2025» / «в 2023–2025»
    text = re.sub(
        r"(?i)(\b[св]\s+)?(?<![\d.,])(\d{4})\s*[-–—]\s*(\d{4})(?![\d.,]|\s*г\.)",
        _years_range,
        text,
    )
    # «50-57%» → от … до … процентов (иначе % съедает правое число раньше диапазона)
    text = re.sub(
        r"(?<![\d.,])(\d+)\s*[-–—]\s*(\d+)\s*%",
        lambda m: f"от {_num_gent(int(m.group(1)))} до {_num_gent(int(m.group(2)))} процентов",
        text,
    )
    # полтора
    text = re.sub(r"(?<![\d.,])1[.,]5\s*(раза|часа|года|литра|метра|километра)\b", r"полтора \1", text)
    # «б/с» (баррелей в сутки)
    text = re.sub(r"(?i)(?<![А-Яа-яЁё])б/с(?![А-Яа-яЁё])", "баррелей в сутки", text)
    for pat, rep in _ABBR_SPOKEN:
        text = re.sub(pat, rep, text)
    return text


# ---------------------------------------------------------------- post-normalize

_HUNDREDS = r"(?:сто|двести|триста|четыреста|пятьсот|шестьсот|семьсот|восемьсот|девятьсот)"


def post_normalize(text: str, source: str = "") -> str:
    # «одна тысяча семьсот…» → «тысяча семьсот…»
    text = re.sub(rf"(?i)\bодна тысяча (?={_HUNDREDS}\b)", "тысяча ", text)
    # «трёхчасов» — normalizr склеивает числительное с «часов»
    text = re.sub(
        r"(?i)\b(одного|двух|трёх|трех|четырёх|четырех|пяти|шести|семи|восьми|девяти|десяти|"
        r"одиннадцати|двенадцати|двадцати|тридцати|сорока)(час(?:ов|а|ам|ами|ах)?)\b",
        r"\1 \2",
        text,
    )
    # normalizr подменяет «человек» на «людей» после числительных
    if re.search(r"(?i)\bчеловек\b", source):
        text = re.sub(
            r"(?i)\b(тысяч|тысячи|миллионов|миллиона|миллион|сот|десят|сорока|ста)\s+людей\b",
            r"\1 человек",
            text,
        )
    return text


# ---------------------------------------------------------------- post-stress

_VSE_RE = re.compile(r"(?<![А-Яа-яЁё+])([Вв])(?:се|сё)(?![А-Яа-яЁё+])")
# «всё больше», «всё равно» — сильнее, чем «мы все»: «мы всё больше атомизируемся»
_COMPARATIVE_NEXT = {
    "более", "больше", "меньше", "менее", "ещё", "еще", "равно", "хуже", "лучше",
}
# «всё это», «всё о …» — но после «мы/вы/они» это «все»: «мы все это видели»
_ALWAYS_YO_NEXT = {"это", "то", "так", "о", "об", "про", "время", "остальное", "сразу"}
_PL_PRON = {"мы", "вы", "они"}
_TOKEN = re.compile(r"[А-Яа-яЁё+́-]+|[^\sА-Яа-яЁё+́-]")


def _plain(tok: str) -> str:
    return tok.replace("+", "").replace("́", "").lower()


def _decide_vse(prev2: str, prev: str, nxt: str, nxt2: str) -> str | None:
    """'все' / 'всё' / None (не уверены → оставить как есть)."""
    if nxt in _COMPARATIVE_NEXT:
        return "всё"
    if prev in _PL_PRON:
        return "все"
    if nxt in _ALWAYS_YO_NEXT:
        return "всё"
    if nxt == ",":
        if nxt2 in ("кто", "которые", "которых"):
            return "все"
        if nxt2 in ("что", "чего", "чем"):
            return "всё"
        return None
    if prev in _PL_PRON:
        return "все"
    m = _morph()
    if nxt in (".", "!", "?", "…", ";", ":", ")", '"') or not nxt:
        if prev == "не" and m is not None and prev2:
            if any("VERB" in p.tag and "plur" in p.tag for p in m.parse(prev2)):
                return "все"
            return None
        if prev == "не":
            return None
        return "всё"
    if m is None or not re.fullmatch(r"[а-яё-]+", nxt):
        return None
    parses = m.parse(nxt)[:4]
    pos_ok = [p for p in parses if p.tag.POS in ("NOUN", "ADJF", "PRTF", "NPRO", "VERB", "NUMR")]
    if not pos_ok:
        return None
    if all("plur" in p.tag for p in pos_ok):
        return "все"
    if all(("sing" in p.tag and "neut" in p.tag) or ("VERB" in p.tag and "sing" in p.tag and "3per" in p.tag)
           for p in pos_ok):
        return "всё"
    return None


def fix_vse(text: str) -> str:
    toks = _TOKEN.findall(text)
    if not any(_plain(t) in ("все", "всё") for t in toks):
        return text
    out = []
    pos = 0
    for m in _VSE_RE.finditer(text):
        start = m.start()
        before = _TOKEN.findall(text[max(0, start - 60):start])
        after = _TOKEN.findall(text[m.end():m.end() + 60])
        prev = _plain(before[-1]) if before else ""
        prev2 = _plain(before[-2]) if len(before) > 1 else ""
        nxt = _plain(after[0]) if after else ""
        nxt2 = _plain(after[1]) if len(after) > 1 else ""
        choice = _decide_vse(prev2, prev, nxt, nxt2)
        out.append(text[pos:start])
        if choice is None:
            out.append(m.group(0))
        else:
            out.append(m.group(1) + choice[1:])
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def post_stress(text: str) -> str:
    text = fix_vse(text)
    # «в две тысячи восемнадцатом г+оду» → «год+у» (предложный после порядкового)
    text = re.sub(r"(?i)(\w*\+?\w*(?:ом|ем))\s+г\+оду\b", r"\1 год+у", text)
    return text
