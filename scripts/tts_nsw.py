"""NSW (non-standard words) + prosody helpers for Russian TTS preprocess."""
from __future__ import annotations

import re

_WORD = r"A-Za-zА-Яа-яЁё"

# Римские → порядковые (частые века/главы)
_ORDINAL_MASC = {
    1: "первый",
    2: "второй",
    3: "третий",
    4: "четвёртый",
    5: "пятый",
    6: "шестой",
    7: "седьмой",
    8: "восьмой",
    9: "девятый",
    10: "десятый",
    11: "одиннадцатый",
    12: "двенадцатый",
    13: "тринадцатый",
    14: "четырнадцатый",
    15: "пятнадцатый",
    16: "шестнадцатый",
    17: "семнадцатый",
    18: "восемнадцатый",
    19: "девятнадцатый",
    20: "двадцатый",
    21: "двадцать первый",
    22: "двадцать второй",
    25: "двадцать пятый",
    30: "тридцатый",
}

_ROMAN_BODY = r"(M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))"
# «XXI век» / «Глава XIV» / «раздел IX»
_ROMAN_BEFORE_CTX = re.compile(
    rf"(?i)\b{_ROMAN_BODY}\b(?=\s*(?:век|века|веке|столети|глав[аеуы]|раздел\w*|часть))"
)
_ROMAN_AFTER_CTX = re.compile(
    rf"(?i)\b((?:глав[аеуы]|раздел\w*|част[ьи]|век)\s+){_ROMAN_BODY}\b"
)


def _roman_to_int(s: str) -> int | None:
    s = s.upper()
    if not s or not re.fullmatch(r"[IVXLCDM]+", s):
        return None
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(s):
        v = vals[ch]
        total += -v if v < prev else v
        prev = v
    return total if total > 0 else None


def _num2words_ru(n: int) -> str | None:
    try:
        from num2words import num2words

        return num2words(n, lang="ru")
    except Exception:
        return None


def expand_latin_etc(text: str) -> str:
    """etc. / etc / et cetera → эт сетера (как просит озвучка)."""
    text = re.sub(r"(?i)\bet\s+cetera\b", "эт сетера", text)
    # \b после etc — не режем etch/etcetera на «etc»+хвост
    text = re.sub(r"(?i)\betc\.?\b", "эт сетера", text)
    return text


# (1 / 2-4 / 5+) формы шкалы после числительного
_SCALE_FORMS = {
    "тыс": ("тысяча", "тысячи", "тысяч"),
    "млн": ("миллион", "миллиона", "миллионов"),
    "млрд": ("миллиард", "миллиарда", "миллиардов"),
    "трлн": ("триллион", "триллиона", "триллионов"),
}


def _scale_word(abbr: str, num_raw: str) -> str:
    forms = _SCALE_FORMS[abbr.lower()]
    try:
        n = int(float(num_raw.replace(",", ".")))
    except Exception:
        return forms[2]
    n100 = abs(n) % 100
    n10 = abs(n) % 10
    if 11 <= n100 <= 14:
        return forms[2]
    if n10 == 1:
        return forms[0]
    if 2 <= n10 <= 4:
        return forms[1]
    return forms[2]


def _cur_word(token: str) -> str:
    t = token.strip().lower()
    if t in ("€", "eur", "евро"):
        return "евро"
    if t in ("$", "usd", "долларов", "доллара", "доллар"):
        return "долларов"
    return token


def _fmt_num(n: str) -> str:
    raw = n.replace(",", ".")
    try:
        if "." in raw:
            w = _num2words_ru(float(raw))  # type: ignore[arg-type]
        else:
            w = _num2words_ru(int(raw))
    except Exception:
        w = None
    return w if w else n


def expand_scale_abbrevs(text: str) -> str:
    """млн./млрд./тыс. → миллионов/… (анти «мэлэнэ» от SpeechKit).

    Важно: сначала «15 € млн», иначе получается «15 евро млн» → буквы.
    Порядок в русской речи: число + шкала + валюта.
    """
    # 15 € млн. / 15€млн / 15 $ млрд
    text = re.sub(
        r"(\d+(?:[.,]\d+)?)\s*([€$]|eur|usd)\s*(тыс|млн|млрд|трлн)\.?",
        lambda m: f"{_fmt_num(m.group(1))} {_scale_word(m.group(3), m.group(1))} {_cur_word(m.group(2))}",
        text,
        flags=re.I,
    )
    # €15 млн / $15 млрд
    text = re.sub(
        r"([€$])\s*(\d+(?:[.,]\d+)?)\s*(тыс|млн|млрд|трлн)\.?",
        lambda m: f"{_fmt_num(m.group(2))} {_scale_word(m.group(3), m.group(2))} {_cur_word(m.group(1))}",
        text,
        flags=re.I,
    )
    # 15 млн € / 15 млн. евро / 15 млн долларов
    text = re.sub(
        r"(\d+(?:[.,]\d+)?)\s*(тыс|млн|млрд|трлн)\.?\s*([€$]|евро|долларов|доллара|доллар|eur|usd)\b",
        lambda m: f"{_fmt_num(m.group(1))} {_scale_word(m.group(2), m.group(1))} {_cur_word(m.group(3))}",
        text,
        flags=re.I,
    )
    # 15 млн / 15 млн.
    text = re.sub(
        r"(\d+(?:[.,]\d+)?)\s*(тыс|млн|млрд|трлн)\.?\b",
        lambda m: f"{_fmt_num(m.group(1))} {_scale_word(m.group(2), m.group(1))}",
        text,
        flags=re.I,
    )
    # остатки голых млн. / млрд. → форма мн.ч. род.п. (без числа)
    for abbr, forms in _SCALE_FORMS.items():
        text = re.sub(
            rf"(?i)(?<![А-Яа-яЁёA-Za-z0-9]){abbr}\.?(?![А-Яа-яЁёA-Za-z0-9])",
            forms[2],
            text,
        )
    return text


def _year_ordinal(year: str, case: str = "nomn") -> str:
    try:
        from num2words import num2words
        phrase = num2words(int(year), to="ordinal", lang="ru")
        words = phrase.split()
        if case != "nomn":
            import pymorphy3
            inflected = pymorphy3.MorphAnalyzer().parse(words[-1])[0].inflect({case})
            if inflected:
                words[-1] = inflected.word
        return " ".join(words)
    except Exception:
        return year


def expand_years(text: str) -> str:
    """Expand Russian year notation before general normalization."""
    text = re.sub(
        r"\b(\d{4})\s*[-–]\s*(\d{4})\s*г\.г\.",
        lambda m: f"с {_year_ordinal(m.group(1), 'gent')} по {_year_ordinal(m.group(2))} год",
        text, flags=re.I,
    )
    return re.sub(
        r"\b(\d{4})\s*г\.",
        lambda m: f"{_year_ordinal(m.group(1))} год",
        text, flags=re.I,
    )


def expand_nsw(text: str) -> str:
    """Расширение NSW до STRESS: %, валюты, млн, диапазоны, римские, etc."""
    text = expand_years(text)
    text = re.sub(r"(?<![А-Яа-яЁё])([А-ЯЁ][а-яё-]+)\s+I\b", r"\1 Первый", text)
    text = expand_latin_etc(text)
    # млн/млрд до голого «€», иначе «15 евро млн» → «мэлэнэ»
    text = expand_scale_abbrevs(text)

    # 15% / 15 % → пятнадцать процентов (или «15 процентов» если нет num2words)
    def _pct(m: re.Match[str]) -> str:
        return f"{_fmt_num(m.group(1))} процентов"

    text = re.sub(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*%", _pct, text)

    # $100 / 100$ → сто долларов (после scale-compound)
    def _money(m: re.Match[str], unit: str) -> str:
        return f"{_fmt_num(m.group(1))} {unit}"

    text = re.sub(r"\$\s*(\d+(?:[.,]\d+)?)\b", lambda m: _money(m, "долларов"), text)
    text = re.sub(r"\b(\d+(?:[.,]\d+)?)\s*\$", lambda m: _money(m, "долларов"), text)
    text = re.sub(r"€\s*(\d+(?:[.,]\d+)?)\b", lambda m: _money(m, "евро"), text)
    text = re.sub(r"\b(\d+(?:[.,]\d+)?)\s*€", lambda m: _money(m, "евро"), text)

    # 10-15 кг / 10–15 → от десяти до пятнадцати (килограммов)
    _u_names = {
        "кг": "килограммов",
        "км": "километров",
        "мм": "миллиметров",
        "м": "метров",
        "км/ч": "километров в час",
    }

    def _range(m: re.Match[str]) -> str:
        a, b = int(m.group(1)), int(m.group(2))
        unit = (m.group(3) or "").lower()
        wa, wb = _num2words_ru(a), _num2words_ru(b)
        core = f"от {wa} до {wb}" if wa and wb else f"от {a} до {b}"
        if unit:
            return f"{core} {_u_names.get(unit, unit)}"
        return core

    text = re.sub(
        r"\b(\d+)\s*[-–—]\s*(\d+)(?:\s*(кг|км/ч|км|мм|м)\b)?",
        _range,
        text,
    )

    # XXI век / Глава XIV
    def _roman_ord(roman: str) -> str | None:
        n = _roman_to_int(roman)
        if n is None:
            return None
        return _ORDINAL_MASC.get(n) or _num2words_ru(n)

    def _roman_before(m: re.Match[str]) -> str:
        return _roman_ord(m.group(1)) or m.group(0)

    def _roman_after(m: re.Match[str]) -> str:
        ord_w = _roman_ord(m.group(2))
        return f"{m.group(1)}{ord_w}" if ord_w else m.group(0)

    text = _ROMAN_BEFORE_CTX.sub(_roman_before, text)
    text = _ROMAN_AFTER_CTX.sub(_roman_after, text)

    # частые единицы после числа (если normalizr не взял)
    unit_map = [
        (r"\b(\d+)\s*кг\b", "килограммов"),
        (r"\b(\d+)\s*км\b", "километров"),
        (r"\b(\d+)\s*км/ч\b", "километров в час"),
        (r"\b(\d+)\s*м\b(?!\w)", "метров"),
        (r"\b(\d+)\s*мм\b", "миллиметров"),
    ]
    for pat, unit in unit_map:
        def _u(m: re.Match[str], u: str = unit) -> str:
            w = _num2words_ru(int(m.group(1)))
            return f"{w} {u}" if w else f"{m.group(1)} {u}"

        text = re.sub(pat, _u, text)

    return text


# Валидная разметка пауз Yandex. Голые «<»/«>» движок читает как «меньше/больше чем».
_SIL_MARK_RE = re.compile(r"sil<\[\d+\]>|<\[[a-z]+\]>", re.IGNORECASE)

# Перед «то» не ставим разрыв: предлоги/союзы («про то, как…»).
_TO_PREV_BLOCK = frozenset(
    {
        "про",
        "а",
        "не",
        "ни",
        "и",
        "или",
        "но",
        "да",
        "вот",
        "вон",
        "как",
        "так",
        "если",
        "тем",
        "потому",
        "оттого",
        "зато",
        "либо",
        "чем",
        "все",
        "всё",
        "то",
        "это",
        "само",
        "всего",
        "только",
        "именно",
        "хотя",
        "ведь",
    }
)
# После частицы «то, …». «как» здесь есть («то, как»), но не в общей запятой:
# иначе «про то, как» получает паузу, хотя этот оборот трогать нельзя.
_TO_AFTER = (
    "чтобы",
    "который",
    "которая",
    "которое",
    "которые",
    "откуда",
    "когда",
    "будто",
    "чего",
    "что",
    "как",
    "где",
)
_REL_AFTER = (
    "чтобы",
    "который",
    "которая",
    "которое",
    "которые",
    "которых",
    "откуда",
    "когда",
    "будто",
    "словно",
    "чего",
    "куда",
    "что",
    "где",
)
_VOWELS_FLEX = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")


def _flex_token(word: str) -> str:
    """Слово с необязательным ``+`` и акутом. Совпадает и с ``т+о``, и с ``то``."""
    parts: list[str] = []
    for ch in word:
        if ch in _VOWELS_FLEX:
            parts.append(r"\+?" + re.escape(ch) + r"\u0301?")
        else:
            parts.append(r"\+?" + re.escape(ch))
    return "".join(parts)


def _strip_stress_token(word: str) -> str:
    return word.replace("+", "").replace("\u0301", "").casefold()


def map_outside_speech_marks(text: str, fn) -> str:
    """Пропустить ``sil<[N]>`` и ``<[tiny]>`` мимо функции, которая их портит.

    ru-normalizr превращает ``sil<[800]>`` в ``sil<>``. Дальше скобки
    вычищаются, и SpeechKit читает оставшееся «sil» как «сил».
    """
    # Пробелы вокруг метки оставляем на ней: нормализатор съедает край сегмента,
    # и без этого получается «Введение.sil<[800]>».
    parked = re.compile(
        r"[ \t]*sil<\[\d+\]>[ \t]*|[ \t]*<\[[a-z]+\]>[ \t]*",
        re.IGNORECASE,
    )
    bits = parked.split(text)
    marks = parked.findall(text)
    out: list[str] = []
    for i, bit in enumerate(bits):
        out.append(fn(bit) if bit else "")
        if i < len(marks):
            out.append(marks[i])
    return "".join(out)


def drop_spoken_sil(text: str) -> str:
    """Убрать слово ``sil`` / ``Sil``, которое SpeechKit читает как «сил».

    Настоящая пауза ``sil<[500]>`` остаётся. Съеденная (``Sil``, ``Sil < >``,
    ``s+il``) — нет: она встаёт сразу после заголовка, то есть в начале ролика.
    """
    text = re.sub(r"(?i)\bs\+?il\s*<\s*>", " ", text)
    text = re.sub(
        r"(?i)(?<![A-Za-zА-Яа-яЁё])s\+?il(?!\s*<\[)",
        " ",
        text,
    )
    return re.sub(r" {2,}", " ", text)


def sanitize_angle_brackets(text: str) -> str:
    """Убрать голые <> / >< / < / >, которые SpeechKit произносит вслух.

    ``sil<[500]>`` и ``<[tiny]>`` сохраняем. Иначе ``<>`` → «больше чем меньше чем».
    """
    slots: list[str] = []

    def _park(m: re.Match[str]) -> str:
        slots.append(m.group(0))
        return f"\0SIL{len(slots) - 1}\0"

    text = _SIL_MARK_RE.sub(_park, text)
    text = text.replace("<>", " ").replace("><", " ")
    text = re.sub(r"[<>]", " ", text)
    for i, mark in enumerate(slots):
        text = text.replace(f"\0SIL{i}\0", mark)
    text = re.sub(r" {2,}", " ", text)
    return text


def strip_speechkit_markup(text: str) -> str:
    """Убрать Yandex sil<> / <[tiny]> перед Silero/Edge/Gemini (иначе «больше чем…»)."""
    text = re.sub(r"sil<\[\d+\]>", "…", text)
    text = re.sub(r"<\[[a-z]+\]>", " ", text, flags=re.IGNORECASE)
    return sanitize_angle_brackets(text)


_LEADING_SIL_RE = re.compile(
    r"^(?:\s*(?:sil<\[\d+\]>|<\[[a-z]+\]>))+",
    re.IGNORECASE,
)


def reattach_leading_sil_marks(chunks: list[str]) -> list[str]:
    """Пауза в начале куска принадлежит концу предыдущего.

    Иначе SpeechKit открывает реплику с ``sil<[250]>, что…``: пауза
    отрывается от слова перед запятой, а при битой разметке снова
    вылезает произносимое «сил».
    """
    if not chunks:
        return chunks
    out: list[str] = []
    for chunk in chunks:
        piece = chunk.strip()
        if not piece:
            continue
        mark = _LEADING_SIL_RE.match(piece)
        if mark and out:
            out[-1] = f"{out[-1].rstrip()} {mark.group(0).strip()}".strip()
            piece = piece[mark.end() :].lstrip()
            if not piece:
                continue
        out.append(piece)
    return out


def split_speech_text(text: str, max_len: int) -> list[str]:
    """Нарезка озвучки: абзацы → предложения → hard-slice, без leading sil."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        cand = f"{buf}\n\n{para}".strip() if buf else para
        if len(cand) <= max_len:
            buf = cand
            continue
        if buf:
            if len(buf) < 300:
                chunks.extend(hard_slices_preserving_sil(cand, max_len))
                buf = ""
                continue
            chunks.append(buf)
            buf = ""
        if len(para) <= max_len:
            buf = para
            continue
        sentences = re.split(r"(?<=[.!?…])\s+", para)
        for sent in sentences:
            if not sent:
                continue
            cand = f"{buf} {sent}".strip() if buf else sent
            if len(cand) <= max_len:
                buf = cand
                continue
            if buf:
                if len(buf) < 300:
                    chunks.extend(hard_slices_preserving_sil(cand, max_len))
                    buf = ""
                    continue
                chunks.append(buf)
            if len(sent) <= max_len:
                buf = sent
            else:
                chunks.extend(hard_slices_preserving_sil(sent, max_len))
                buf = ""
        if buf:
            chunks.append(buf)
            buf = ""
    if buf:
        chunks.append(buf)
    return reattach_leading_sil_marks(chunks)


def hard_slices_preserving_sil(text: str, max_len: int) -> list[str]:
    """Жёсткая нарезка без разрыва sil<[N]> / <[tiny]>."""
    if len(text) <= max_len:
        return [text]
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + max_len, n)
        if end < n:
            for m in _SIL_MARK_RE.finditer(text[i : min(n, i + max_len + 40)]):
                a, b = i + m.start(), i + m.end()
                if a < end < b:
                    end = a
                    break
            if end <= i:
                end = min(i + max_len, n)
            token_start = text.rfind(" ", i, end) + 1
            token_end = text.find(" ", end)
            if token_end < 0:
                token_end = n
            if token_start < end < token_end:
                end = token_end
            sp = text.rfind(" ", i + max_len // 2, end)
            if sp > i:
                end = sp
            # Если следующий кусок начнётся с sil — забираем метку в текущий.
            rest = text[end:n].lstrip()
            lead = _LEADING_SIL_RE.match(rest)
            if lead and end + (len(text[end:n]) - len(rest)) + lead.end() - i <= max_len + 40:
                end = end + (len(text[end:n]) - len(rest)) + lead.end()
        piece = text[i:end].strip()
        if piece:
            out.append(piece)
        i = end if end > i else i + max_len
        while i < n and text[i].isspace():
            i += 1
    return reattach_leading_sil_marks(out)


def apply_prosody_pauses(text: str) -> str:
    """Форсируем паузы, которые SpeechKit часто глотает.

    Типичный баг: «сказал то, чего…» → «сказалто …… чего».
    Частица «то» слипается с глаголом, запятая не даёт границу.
    Заголовки уже получают sil<[800]> в prepare_md_for_tts.
    """
    # 0) пауза между абзацами (если в конце абзаца ещё нет sil<[…]>)
    def _para_pause(m: re.Match[str]) -> str:
        left = m.group(1)
        if re.search(r"sil<\[\d+\]>\s*$", left):
            return m.group(0)
        return left + " sil<[500]>\n\n"

    text = re.sub(r"([^\n]+)\n\s*\n", _para_pause, text)

    # 0b) прямая речь (тире), НЕ маркированный список «- Глава…» из оглавления
    text = re.sub(r"(?m)^(?:—|–)\s+", "sil<[300]> ", text)

    # 1) частица «то» после слова. «т+о» / «чег+о» — тот же случай, что и без «+»:
    # silero ставит ударение раньше этой функции, голый «то» в бою уже не встречается.
    # «про то, как» не трогаем.
    prev = rf"(?:[{_WORD}][{_WORD}+\u0301]*)"
    particle = _flex_token("то")
    after = "(?:" + "|".join(_flex_token(w) for w in _TO_AFTER) + ")"

    def _pause_to(m: re.Match[str]) -> str:
        left, tok = m.group(1), m.group(2)
        if _strip_stress_token(left) in _TO_PREV_BLOCK:
            return m.group(0)
        return f"{left} — sil<[600]> {tok} sil<[500]>, "

    text = re.sub(
        rf"(?<![{_WORD}])({prev})\s+({particle})\s*,\s*(?={after})",
        _pause_to,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"(?:^|(?<=[.!?…]\s))({particle})\s*,\s*(?={after})",
        lambda m: f"{m.group(1)} sil<[500]>, ",
        text,
        flags=re.IGNORECASE,
    )

    # Запятая перед частицей тоже не всегда создаёт акустическую границу:
    # «это легко, то ...» SpeechKit может слить в «легкото».
    # Не вмешиваемся в устойчивое «то есть».
    text = re.sub(
        r",\s+то\b(?!\s+есть)",
        ", sil<[400]> то",
        text,
        flags=re.IGNORECASE,
    )

    # 2) запятая перед относительными — пауза (не трогаем уже размеченные sil<> / <[…]> )
    relative = "(?:" + "|".join(_flex_token(w) for w in _REL_AFTER) + ")"
    text = re.sub(
        rf"(?<!]>),\s+(?={relative})",
        " sil<[250]>, ",
        text,
        flags=re.IGNORECASE,
    )

    # 3) не дублировать sil рядом
    text = re.sub(r"(sil<\[\d+\]>\s*){2,}", r"\1", text)
    text = sanitize_angle_brackets(text)
    text = re.sub(r" {2,}", " ", text)
    return text
