#!/usr/bin/env python3
"""Prepare manuscript for TTS.

Pipeline:
  1) strip markdown / editorial noise
  2) ru-normalizr light — numbers/dates (no letter-spell initials, no IPA)
  3) silero-stress if PDF_AUDIO_STRESS≠off
     - PDF_AUDIO_STRESS_FORMAT=acute (default) → U+0301 for Edge
     - PDF_AUDIO_STRESS_FORMAT=plus → keep `п+окер` for Silero TTS
  4) never pass literal spaced "+" as «плюс» to Edge
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path

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
    if not title.endswith((".", "!", "?")):
        title += "."
    return title


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
        return _light_cleanup(_heading_to_speech(stripped))
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
            opts = NormalizeOptions.tts(
                initials_pause_mode="preserve",
                enable_letter_abbreviation_expansion=False,
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
    mode = (os.getenv("PDF_AUDIO_NORMALIZE_MODE") or "light").strip().lower()
    if mode in ("off", "0", "none"):
        return text
    norm = _get_normalizer()
    if norm is None:
        return text
    parts: list[str] = []
    for para in re.split(r"(\n\s*\n)", text):
        if not para.strip() or para.isspace() or re.fullmatch(r"\n\s*\n", para):
            parts.append(para)
            continue
        parts.append(norm.normalize(para))
    return _fix_literal_plus("".join(parts))


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
    """Speech-ready text: light normalize → silero-stress.

    Формат ударений: PDF_AUDIO_STRESS_FORMAT=acute (Edge) или plus (Silero TTS).
    Порядок: сначала нормализация, потом ударения — иначе normalizer
    превращает `о́` в `+о`, а фикс плюсов ломает слово в « и о».
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
