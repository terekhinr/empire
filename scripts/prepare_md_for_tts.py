#!/usr/bin/env python3
"""Prepare markdown manuscript for TTS: strip markup, fix symbols, readable prose."""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

_ROMAN = {
    "I": "первая",
    "II": "вторая",
    "III": "третья",
    "IV": "четвёртая",
    "V": "пятая",
    "VI": "шестая",
    "VII": "седьмая",
    "VIII": "восьмая",
    "IX": "девятая",
    "X": "десятая",
}

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


def _roman_part(text: str) -> str:
    m = re.search(r"ЧАСТЬ\s+([IVX]+)\b", text, re.I)
    if not m:
        return text
    word = _ROMAN.get(m.group(1).upper())
    if word:
        return re.sub(r"ЧАСТЬ\s+[IVX]+\b", f"Часть {word}", text, flags=re.I)
    return text


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


_MOEX_NAMES = {
    "PLZL": "Полюс",
    "SBER": "Сбер",
    "MDMG": "МД Медикал",
}

_ABBREV_SPEECH = (
    (re.compile(r"\bт\.е\.\b", re.I), "то есть"),
    (re.compile(r"\bт\. д\.\b", re.I), "так далее"),
    (re.compile(r"\bт\.н\.\b", re.I), "так называемый"),
    (re.compile(r"\bимхо\b", re.I), "по моему мнению"),
    (re.compile(r"\bwindfall tax\b", re.I), "налог на сверхприбыли"),
    (re.compile(r"\blook through\b", re.I), "не обращать внимания на"),
    (re.compile(r"\bcredere\b", re.I), "кредере"),
    (re.compile(r"\bGLDRUB_TOM\b"), "золото на бирже"),
    (re.compile(r"\bЦБ\b"), "Центробанк"),
    (re.compile(r"\bEBITDA\b"), "Эбитда"),
    (re.compile(r"\bKPI\b"), "ключевой показатель"),
    (re.compile(r"\bValue and Income\b"), "вэлью энд инкам"),
)


def _strip_urls(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\b(?:www\.)?[a-z0-9][-a-z0-9]*\.(?:ru|com|org)/\S*", "", text, flags=re.I)
    text = re.sub(r"\bt\.me/\S+", "", text, flags=re.I)
    text = re.sub(r"\bsponsr\.ru/\S+", "", text, flags=re.I)
    text = re.sub(r"\bkremlin\.ru/\S+", "", text, flags=re.I)
    text = re.sub(r"#\S+", "", text)
    return text


def _normalize_symbols(text: str) -> str:
    text = text.replace("\u00ad", "")  # soft hyphen
    text = text.replace("\ufe0f", "")  # variation selector
    text = text.replace("…", ".")
    text = text.replace("–", "-")
    text = text.replace("—", " - ")
    text = text.replace("«", "")
    text = text.replace("»", "")
    text = text.replace("„", "")
    text = text.replace("“", "")
    text = text.replace("”", "")
    text = text.replace("§", " раздел ")
    text = text.replace("·", ", ")
    text = text.replace("→", ", ")
    text = text.replace("▸", "")
    text = text.replace("×", " на ")
    text = text.replace("÷", " делить на ")
    text = text.replace("−", "-")
    text = text.replace("²", " в квадрате")
    text = text.replace("₽", " рублей")
    text = re.sub(r"\[Новостной деск\]\s*", "Новостной деск. ", text, flags=re.I)
    text = re.sub(
        r"\[MOEX:\s*([A-Z0-9_]+)\]",
        lambda m: _MOEX_NAMES.get(m.group(1), f"тикер {m.group(1).replace('_', ' ')}"),
        text,
        flags=re.I,
    )
    text = re.sub(r"\$(\d+(?:[.,]\d+)?)", r"\1 долларов", text)
    text = re.sub(r"(\d+(?:[.,]\d+)?)\s*%", r"\1 процентов", text)
    text = re.sub(r"(\d+),(\d+)", r"\1 целая \2", text)
    text = re.sub(r"(\d+)\s*тыс\.", r"\1 тысяч", text)
    text = re.sub(r"км/ч", "километров в час", text)
    text = _strip_urls(text)
    for pat, repl in _ABBREV_SPEECH:
        text = pat.sub(repl, text)
    text = re.sub(r"<\s*(\d)", r"меньше \1", text)
    text = re.sub(r">\s*(\d)", r"больше \1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&", " и ")
    text = re.sub(r"\s*\[\d{1,2}(?:\s*[\-–,;]\s*\d{1,2})*\]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2700-\u27BF⚔⚠☐✍]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _heading_to_speech(line: str) -> str:
    m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
    if not m:
        return line
    title = _strip_markdown_inline(m.group(2).strip())
    title = _roman_part(title)
    title = re.sub(r"^\d+\.\s*", "", title)
    if not title.endswith((".", "!", "?")):
        title += "."
    return title


_EDITORIAL_LINE_PATTERNS = (
    re.compile(r"РАЗМЕТКА АВТОРИТЕТОВ", re.I),
    re.compile(r"Примечание к версии", re.I),
    re.compile(r"^\s*Версия\s+\d+", re.I),
    re.compile(r"\[АВТОРИТЕТ\s*·", re.I),
)


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
            return _normalize_symbols(_strip_markdown_inline(sentence))
        return None
    if stripped.startswith("#"):
        return _normalize_symbols(_heading_to_speech(stripped))
    stripped = _strip_markdown_inline(stripped)
    stripped = re.sub(r"^✍️?\s*", "", stripped)
    stripped = re.sub(r"^\*+\s*", "", stripped)
    stripped = re.sub(r"\*+\s*$", "", stripped)
    stripped = re.sub(r"^ЛИЧНЫЙ ПРИМЕР:\s*", "Личный пример. ", stripped, flags=re.I)
    stripped = _roman_part(stripped)
    stripped = _normalize_symbols(stripped)
    return stripped or None


def prepare_md_for_tts(raw: str) -> str:
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
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r" +([.,;:!?])", r"\1", text)
    return text.strip() + "\n"


def prepare_for_tts(raw: str) -> str:
    """Markdown or plain TTS manuscript -> speech-ready text."""
    return prepare_md_for_tts(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown -> clean text for TTS")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Missing input: {args.input}", file=sys.stderr)
        return 1

    output = args.output or args.input.with_name(f"{args.input.stem}_tts.txt")
    raw = args.input.read_text(encoding="utf-8")
    cleaned = prepare_for_tts(raw)
    output.write_text(cleaned, encoding="utf-8")

    print(f"Input:  {args.input} ({len(raw)} chars)")
    print(f"Output: {output} ({len(cleaned)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
