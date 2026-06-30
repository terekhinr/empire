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
    re.compile(r"^\s*\|?\s*[-:]+\s*\|", re.I),  # |---|---| separators
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
    text = text.replace("<", " меньше ")
    text = text.replace(">", " больше ")
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


def prepare_md_for_tts(raw: str) -> str:
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    skip_meta = True

    for line in lines:
        stripped = line.strip()

        if skip_meta:
            if stripped.startswith("## Благодарности"):
                skip_meta = False
            else:
                continue

        if not stripped:
            if out and out[-1] != "":
                out.append("")
            continue

        if stripped in {"---", "***", "___"}:
            if out and out[-1] != "":
                out.append("")
            continue

        if any(p.search(stripped) for p in _SKIP_LINE_PATTERNS):
            continue

        if stripped.startswith(">"):
            stripped = re.sub(r"^>\s*", "", stripped)

        if stripped.startswith("|"):
            sentence = _table_row_to_sentence(stripped)
            if sentence:
                out.append(_normalize_symbols(_strip_markdown_inline(sentence)))
            continue

        if stripped.startswith("#"):
            out.append(_normalize_symbols(_heading_to_speech(stripped)))
            continue

        stripped = _strip_markdown_inline(stripped)
        stripped = re.sub(r"^✍️?\s*", "", stripped)
        stripped = re.sub(r"^\*+\s*", "", stripped)
        stripped = re.sub(r"\*+\s*$", "", stripped)
        stripped = re.sub(r"^ЛИЧНЫЙ ПРИМЕР:\s*", "Личный пример. ", stripped, flags=re.I)
        stripped = _roman_part(stripped)
        stripped = _normalize_symbols(stripped)
        if stripped:
            out.append(stripped)

    text = "\n\n".join(p for p in ("\n".join(out).split("\n\n")) if p.strip())
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r" +([.,;:!?])", r"\1", text)
    return text.strip() + "\n"


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
    cleaned = prepare_md_for_tts(raw)
    output.write_text(cleaned, encoding="utf-8")

    print(f"Input:  {args.input} ({len(raw)} chars)")
    print(f"Output: {output} ({len(cleaned)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
