#!/usr/bin/env python3
"""Prepare manuscript for TTS.

Pipeline (см. docs/TTS_PRONUNCIATION_PIPELINE.md):
  1) strip markdown / editorial noise
  2) abbreviations + legal forms (АО/ООО → полные слова)
  3) ru-normalizr light — numbers/dates
  4) silero-stress if PDF_AUDIO_STRESS≠off
     - PDF_AUDIO_STRESS_FORMAT=acute (default) → U+0301 for Edge
     - PDF_AUDIO_STRESS_FORMAT=plus → keep `п+окер` for Yandex/Silero
  5) pronunciation lexicon (фонемы/ударения/алиасы) — поверх авто-стресса
  6) never pass literal spaced "+" as «плюс» to Edge
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path

from tts_disambig import apply_homograph_disambiguation  # noqa: E402
from tts_nsw import (  # noqa: E402
    apply_prosody_pauses,
    expand_nsw,
    sanitize_angle_brackets,
    strip_speechkit_markup,
)
from tts_pronunciation import (  # noqa: E402
    apply_pronunciation_lexicon,
    expand_legal_forms,
)

_ACUTE = "\u0301"
_VOWELS_RU = "аеёиоуыэюяАЕЁИОУЫЭЮЯ"

_SKIP_LINE_PATTERNS = (
    re.compile(r"^\s*>\s*.*🔧", re.I),
    re.compile(r"^\s*>\s*\*\*🔧", re.I),
    re.compile(r"^\s*>\s*\*\*Примечание к версии", re.I),
    re.compile(r"АВТОРСКАЯ ВСТАВКА \(не заполняется редактурой\)", re.I),
    re.compile(r"^\s*\|?\s*[-:]+\s*\|", re.I),
    re.compile(r"РАЗМЕТКА АВТОРИТЕТОВ", re.I),
    re.compile(r"Примечание к версии", re.I),
    re.compile(r"^\s*Версия\s+\d+", re.I),
    re.compile(r"\[АВТОРИТЕТ\s*·", re.I),
)

_EDITORIAL_LINE_PATTERNS = (
    re.compile(r"РАЗМЕТКА АВТОРИТЕТОВ", re.I),
    re.compile(r"Примечание к версии", re.I),
    re.compile(r"^\s*Версия\s+\d+", re.I),
    re.compile(r"\[АВТОРИТЕТ\s*·", re.I),
)

_MOEX_NAMES = {
    "PLZL": "Полюс",
    "SBER": "Сбер",
    "MDMG": "МД Медикал",
}


def _table_row_to_sentence(line: str) -> str | None:
    line = line.strip()
    if not line.startswith("|"):
        return None
    cells = [c.strip() for c in line.strip("|").split("|")]
    cells = [c for c in cells if c and not re.fullmatch(r"[-:]+", c)]
    if not cells:
        return None
    if all(re.fullmatch(r"[-:]+", c) for c in cells):
        return None
    if cells[0] in {"#", "№"}:
        cells = cells[1:]
    return ". ".join(cells) + "."


def _strip_markdown_inline(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    return text


def _strip_urls(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\b(?:www\.)?[a-z0-9][-a-z0-9]*\.(?:ru|com|org)/\S*", "", text, flags=re.I)
    text = re.sub(r"\bt\.me/\S+", "", text, flags=re.I)
    text = re.sub(r"\bsponsr\.ru/\S+", "", text, flags=re.I)
    text = re.sub(r"\bkremlin\.ru/\S+", "", text, flags=re.I)
    text = re.sub(r"#\S+", "", text)
    return text


def _light_cleanup(text: str) -> str:
    """Только мусор разметки; нормализацию речи делает ru-normalizr."""
    text = text.replace("\u00ad", "")
    text = text.replace("\ufe0f", "")
    text = text.replace("«", '"').replace("»", '"')
    text = text.replace("„", '"').replace("“", '"').replace("”", '"')
    text = re.sub(r"\[Новостной деск\]\s*", "Новостной деск. ", text, flags=re.I)
    text = re.sub(
        r"\[MOEX:\s*([A-Z0-9_]+)\]",
        lambda m: _MOEX_NAMES.get(m.group(1), f"тикер {m.group(1).replace('_', ' ')}"),
        text,
        flags=re.I,
    )
    text = _strip_urls(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s*\[\d{1,2}(?:\s*[\-–,;]\s*\d{1,2})*\]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2700-\u27BF⚔⚠☐✍]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _heading_to_speech(line: str) -> str:
    m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
    if not m:
        return line
    title = _strip_markdown_inline(m.group(2).strip())
    title = re.sub(r"^\d+\.\s*", "", title)
    title = _light_cleanup(title)
    if not title.endswith((".", "!", "?")):
        title += "."
    # пауза после заголовка (не гонять через _light_cleanup — он ест <…>)
    return f"{title} sil<[800]>"


def _is_url_only_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if re.fullmatch(r"https?://\S+", s):
        return True
    if re.fullmatch(r"(?:t\.me|kremlin\.ru|sponsr\.ru|www\.\S+)\S*", s, flags=re.I):
        return True
    return bool(re.fullmatch(r"[a-z0-9][-a-z0-9./#?=&_%:-]+", s, flags=re.I) and "." in s)


def _process_line(stripped: str) -> str | None:
    if _is_url_only_line(stripped):
        return None
    if any(p.search(stripped) for p in _SKIP_LINE_PATTERNS):
        return None
    if stripped.startswith(">"):
        stripped = re.sub(r"^>\s*", "", stripped)
    if stripped.startswith("|"):
        sentence = _table_row_to_sentence(stripped)
        if sentence:
            return _light_cleanup(_strip_markdown_inline(sentence))
        return None
    if stripped.startswith("#"):
        return _heading_to_speech(stripped)
    stripped = _strip_markdown_inline(stripped)
    stripped = re.sub(r"^✍️?\s*", "", stripped)
    stripped = re.sub(r"^\*+\s*", "", stripped)
    stripped = re.sub(r"\*+\s*$", "", stripped)
    stripped = re.sub(r"^ЛИЧНЫЙ ПРИМЕР:\s*", "Личный пример. ", stripped, flags=re.I)
    stripped = _light_cleanup(stripped)
    return stripped or None


def prepare_md_for_tts(raw: str) -> str:
    """Strip markdown/editorial → plain paragraphs (speech normalize later)."""
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    in_editorial = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if out and out[-1] != "":
                out.append("")
            continue

        if stripped in {"---", "***", "___"}:
            if out and out[-1] != "":
                out.append("")
            continue

        if any(p.search(stripped) for p in _EDITORIAL_LINE_PATTERNS):
            in_editorial = True
            continue

        if in_editorial:
            if stripped.startswith("## Благодарности") or stripped == "Благодарности":
                in_editorial = False
                out.append("Благодарности.")
            continue

        processed = _process_line(stripped)
        if processed:
            out.append(processed)

    text = "\n\n".join(p for p in ("\n".join(out).split("\n\n")) if p.strip())
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +([.,;:!?])", r"\1", text)
    return text.strip() + "\n"


_NORMALIZER = None
_NORMALIZER_TRIED = False
_ACCENTOR = None
_ACCENTOR_TRIED = False


def _fix_literal_plus(text: str) -> str:
    """Edge читает «+» как «плюс».

    Важно: НЕ трогать `п+окер` (нотация ударения silero-stress).
    Только пробельный плюс и покерный суффикс «АК+».
    """
    # «Вова + Настя» — плюс с пробелами
    text = re.sub(r"(?<=\w)\s+\+\s+(?=\w)", " и ", text)
    # «АК+» / «KK+» в конце токена (не `п+окер`)
    text = re.sub(
        r"\b([A-Za-zА-Яа-яЁё]{1,4})\+(?=[\s.,;:!?»\")\]]|$)",
        r"\1 и выше",
        text,
    )
    return text


# Только явные женские фамильные хвосты (fallback без pymorphy).
_FEM_SURNAME_TAIL = re.compile(
    r"(?:ова|ева|ёва|ина|ына|ая|яя|ская|цкая)$",
    re.I,
)
_FEM_FIRST_NAMES = frozenset(
    """
    анна мария марья елена ольга наталья наталия татьяна екатерина ирина
    светлана юлия марина виктория александра валентина галина людмила
    надежда вера любовь люба софья софия дарья анастасия полина
    алиса вероника ксения евгения валерия
    """.split()
)

_MORPH_UV = None
_MORPH_UV_TRIED = False


def _get_morph_uv():
    global _MORPH_UV, _MORPH_UV_TRIED
    if _MORPH_UV_TRIED:
        return _MORPH_UV
    _MORPH_UV_TRIED = True
    try:
        import pymorphy3

        _MORPH_UV = pymorphy3.MorphAnalyzer()
    except Exception:
        try:
            import pymorphy2

            _MORPH_UV = pymorphy2.MorphAnalyzer()
        except Exception:
            _MORPH_UV = None
    return _MORPH_UV


def _uv_form_for_word(word: str) -> str:
    """Согласовать «уважаемый» по роду/падежу/числу со следующим словом.

    ув. Эдуарда → уважаемого; ув. Петровой → уважаемой; ув. Петрова → уважаемая.
    """
    low = word.casefold().replace("ё", "е")
    morph = _get_morph_uv()

    def _inflect(tags: set) -> str | None:
        if morph is None or not tags:
            return None
        base = morph.parse("уважаемый")[0]
        inf = base.inflect(tags)
        return inf.word if inf else None

    # «Петрова» pymorphy часто считает masc gent «Петрова» > femn nomn.
    # В обращении «ув. Петрова» это почти всегда женская фамилия им.п.
    if _FEM_SURNAME_TAIL.search(low) or low in _FEM_FIRST_NAMES:
        if morph is not None:
            for p in morph.parse(word):
                if "femn" not in p.tag:
                    continue
                tags = {
                    x
                    for x in (
                        getattr(p.tag, "gender", None),
                        getattr(p.tag, "case", None),
                        getattr(p.tag, "number", None),
                    )
                    if x
                }
                form = _inflect(tags)
                if form:
                    return form
        return "уважаемая"

    if morph is None:
        return "уважаемый"

    base_parses = morph.parse(word)
    ranked = sorted(
        base_parses,
        key=lambda p: (
            0 if ("Name" in p.tag or "Surn" in p.tag or "Patr" in p.tag) else 1,
            0 if "NOUN" in p.tag else 1,
            0 if "anim" in p.tag else 1,
            # Эдуарда: masc gent/acc важнее редкого femn nomn
            0 if ("masc" in p.tag and ("gent" in p.tag or "accs" in p.tag)) else 1,
            1 if ("femn" in p.tag and "nomn" in p.tag and "Name" in p.tag) else 0,
            -p.score,
        ),
    )
    for p in ranked[:8]:
        tags = {
            x
            for x in (
                getattr(p.tag, "gender", None),
                getattr(p.tag, "case", None),
                getattr(p.tag, "number", None),
            )
            if x
        }
        form = _inflect(tags)
        if form:
            return form
    return "уважаемый"


def _expand_uv_title(match: re.Match[str]) -> str:
    """Ув. X → уважаемый/уважаемого/уважаемой… по морфологии X."""
    trailing = match.group(1) or ""
    nxt = re.match(r"\s*([А-ЯЁа-яё-]+)", trailing)
    word = (nxt.group(1) if nxt else "").strip()
    if not word:
        return f"уважаемый{trailing}"
    return f"{_uv_form_for_word(word)}{trailing}"


def expand_speech_abbreviations(text: str) -> str:
    """Расшифровка сокращений для озвучки (до/после normalizr).

    Примеры: ув. → уважаемый/ая, т.д. → так далее, АО/ООО → юрформы.
    """
    # --- составные и однозначные (точка обязательна у коротких) ---
    repls: list[tuple[str, str]] = [
        (r"(?i)\bв\s*т\.\s*ч\.", "в том числе"),
        (r"(?i)\bи\s*т\.\s*д\.", "и так далее"),
        (r"(?i)\bи\s*т\.\s*п\.", "и тому подобное"),
        (r"(?i)\bи\s*др\.", "и другие"),
        (r"(?i)\bт\.\s*д\.", "так далее"),
        (r"(?i)\bт\.\s*п\.", "тому подобное"),
        (r"(?i)\bт\.\s*е\.", "то есть"),
        (r"(?i)\bт\.\s*к\.", "так как"),
        (r"(?i)\bт\.\s*н\.", "так называемый"),
        (r"(?i)\bнапр\.", "например"),
        (r"(?i)\bпроч\.", "прочее"),
        (r"(?i)\bсм\.", "смотри"),
        (r"(?i)\bрис\.", "рисунок"),
        (r"(?i)\bтабл\.", "таблица"),
        (r"(?i)\bстр\.", "страница"),
        (r"(?i)\bгл\.", "глава"),
        (r"(?i)\bп\.\s*(?=\d)", "пункт "),
        (r"(?i)\bг-жа\b", "госпожа"),
        (r"(?i)\bг-н\b", "господин"),
        (r"(?i)\bул\.", "улица"),
        (r"(?i)\bок\.\s*(?=\d)", "около "),
        # лат. etc. — до NSW; дубль в expand_nsw
        (r"(?i)\bet\s+cetera\b", "эт сетера"),
        (r"(?i)\betc\.?\b", "эт сетера"),
        # млн/млрд/тыс — НЕ здесь: иначе «15 € млн» → «15 евро миллионов».
        # Шкалы раскрывает tts_nsw.expand_scale_abbrevs (число+шкала+валюта).
    ]
    for pat, rep in repls:
        text = re.sub(pat, rep, text)

    # Ув. / ув. — с учётом рода следующего слова
    text = re.sub(r"(?i)\bув\.(\s*[А-ЯЁа-яё-]*)", _expand_uv_title, text)

    # «Др. Иванов» в начале обращения → доктор (не трогаем «и другие»)
    text = re.sub(r"(?i)(?<!\w)др\.\s+(?=[А-ЯЁ])", "доктор ", text)

    # ООО / АО / ПАО… (гео-АО → автономный округ/область)
    text = expand_legal_forms(text)

    text = re.sub(r" {2,}", " ", text)
    return text


def _get_normalizer():
    """ru-normalizr: light по умолчанию (не ломает «Маша Н.» в «Маша эн»)."""
    global _NORMALIZER, _NORMALIZER_TRIED
    if _NORMALIZER_TRIED:
        return _NORMALIZER
    _NORMALIZER_TRIED = True
    try:
        from ru_normalizr import NormalizeOptions, Normalizer

        mode = (os.getenv("PDF_AUDIO_NORMALIZE_MODE") or "light").strip().lower()
        if mode in ("safe",):
            opts = NormalizeOptions.safe()
        elif mode in ("full", "tts", "aggressive"):
            opts = NormalizeOptions.tts(
                initials_pause_mode="preserve",
                initials_vowel_mode="single",
            )
        else:
            # letter abbreviations ON — т.д./т.п./см./рис.; инициалы выкл.
            opts = NormalizeOptions.tts(
                initials_pause_mode="preserve",
                enable_letter_abbreviation_expansion=True,
                enable_initials_expansion=False,
                enable_latinization=False,
            )
        _NORMALIZER = Normalizer(opts)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("ru-normalizr unavailable: %s", exc)
        _NORMALIZER = None
    return _NORMALIZER


def _get_accentor():
    global _ACCENTOR, _ACCENTOR_TRIED
    if _ACCENTOR_TRIED:
        return _ACCENTOR
    _ACCENTOR_TRIED = True
    try:
        from silero_stress import load_accentor

        _ACCENTOR = load_accentor()
    except Exception:
        _ACCENTOR = None
    return _ACCENTOR


def _plus_stress_to_acute(text: str) -> str:
    text = re.sub(rf"(?<!\w)\+([{_VOWELS_RU}])(?!\w)", r"\1", text)
    text = re.sub(rf"\+([{_VOWELS_RU}])", lambda m: m.group(1) + _ACUTE, text)
    text = text.replace("+", "")
    text = text.replace(f"ё{_ACUTE}", "ё").replace(f"Ё{_ACUTE}", "Ё")
    return text


def _apply_ru_normalizr(text: str) -> str:
    text = _fix_literal_plus(text)
    text = expand_speech_abbreviations(text)
    text = expand_nsw(text)
    mode = (os.getenv("PDF_AUDIO_NORMALIZE_MODE") or "light").strip().lower()
    if mode in ("off", "0", "none"):
        return expand_speech_abbreviations(expand_nsw(text))
    norm = _get_normalizer()
    if norm is None:
        return expand_speech_abbreviations(expand_nsw(text))
    parts: list[str] = []
    for para in re.split(r"(\n\s*\n)", text):
        if not para.strip() or para.isspace() or re.fullmatch(r"\n\s*\n", para):
            parts.append(para)
            continue
        parts.append(norm.normalize(para))
    # ещё раз — normalizr мог оставить пробелы/точки; добить «ув.» / etc / NSW
    text = expand_speech_abbreviations(_fix_literal_plus("".join(parts)))
    return expand_nsw(text)


_STRESS_MAX_CHARS = int(os.getenv("PDF_AUDIO_STRESS_MAX_CHARS", "1200"))


def _stress_chunks(text: str, max_len: int = _STRESS_MAX_CHARS) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_len:
        return [text]
    sentences = re.split(r"(?<=[.!?…])\s+", text)
    out: list[str] = []
    buf = ""
    for sent in sentences:
        if not sent:
            continue
        cand = f"{buf} {sent}".strip() if buf else sent
        if len(cand) <= max_len:
            buf = cand
            continue
        if buf:
            out.append(buf)
        if len(sent) <= max_len:
            buf = sent
        else:
            for i in range(0, len(sent), max_len):
                out.append(sent[i : i + max_len])
            buf = ""
    if buf:
        out.append(buf)
    return out


def _stress_format() -> str:
    """acute = U+0301 (Edge); plus = silero `п+окер` (Silero TTS)."""
    fmt = (os.getenv("PDF_AUDIO_STRESS_FORMAT") or "acute").strip().lower()
    return "plus" if fmt in ("plus", "+", "silero") else "acute"


def _apply_silero_stress(text: str, *, fmt: str | None = None) -> str:
    accentor = _get_accentor()
    if accentor is None:
        return text
    keep_plus = (fmt or _stress_format()) == "plus"
    parts: list[str] = []
    for para in re.split(r"(\n\s*\n)", text):
        if not para.strip() or para.isspace() or re.fullmatch(r"\n\s*\n", para):
            parts.append(para)
            continue
        chunks = []
        for chunk in _stress_chunks(para):
            marked = accentor(chunk)
            chunks.append(marked if keep_plus else _plus_stress_to_acute(marked))
        parts.append(" ".join(chunks))
    return "".join(parts)


def prepare_for_tts(raw: str, *, accent: bool | None = None) -> str:
    """Speech-ready text: normalize → stress → pronunciation lexicon.

    Формат ударений: PDF_AUDIO_STRESS_FORMAT=acute (Edge) или plus (Yandex/Silero).
    Порядок: нормализация → ударения → lexicon (overrides поверх модели).
    Lexicon после стресса: иначе silero-stress может испортить [[фонемы]].
    """
    text = prepare_md_for_tts(raw)
    text = _apply_ru_normalizr(text)
    if accent is None:
        flag = (
            os.getenv("PDF_AUDIO_STRESS")
            or os.getenv("PDF_AUDIO_RUACCENT")
            or "1"
        ).strip().lower()
        accent = flag not in ("0", "false", "no", "off")
    if accent:
        text = _apply_silero_stress(text)
    else:
        # без акцентуатора всё равно не оставляем сырой «+»
        text = _fix_literal_plus(text)
        text = re.sub(r"(?<![A-Za-zА-Яа-яЁё])\+(?![A-Za-zА-Яа-яЁё])", " ", text)
    # P3: после lexicon — иначе плоские k=v перетирают контекст;
    # фразы lexicon (со стороны) уже стоят; disambig добивает остальное.
    lex_flag = (os.getenv("PDF_AUDIO_PRONUNCIATION") or "1").strip().lower()
    if lex_flag not in ("0", "false", "no", "off"):
        text = apply_pronunciation_lexicon(text)
    text = apply_homograph_disambiguation(text)
    # Паузы после lexicon — иначе silero-stress/regex ломают sil<> / <[tiny]>
    prosody = (os.getenv("PDF_AUDIO_PROSODY") or "1").strip().lower()
    if prosody not in ("0", "false", "no", "off"):
        text = apply_prosody_pauses(text)
    # sil<> — только Yandex SpeechKit. Silero/Edge/Gemini иначе читают «больше чем меньше чем».
    prov = (os.getenv("PDF_AUDIO_TTS_PROVIDER") or "").strip().lower()
    if prov not in ("yandex", "speechkit"):
        text = strip_speechkit_markup(text)
    else:
        text = sanitize_angle_brackets(text)
    # Edge/Gemini: «+» из lexicon не нативен (в отличие от Silero/Yandex).
    if prov in ("edge", "gemini"):
        text = re.sub(r"\+(?=[\u0400-\u04FF])", "", text)
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown → TTS text")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    if not args.input.is_file():
        print(f"Missing input: {args.input}", file=sys.stderr)
        return 1
    output = args.output or args.input.with_name(f"{args.input.stem}_tts.txt")
    cleaned = prepare_for_tts(args.input.read_text(encoding="utf-8"))
    output.write_text(cleaned, encoding="utf-8")
    print(f"Input:  {args.input} ({args.input.stat().st_size} bytes)")
    print(f"Output: {output} ({len(cleaned)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
