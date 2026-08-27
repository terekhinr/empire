#!/usr/bin/env python3
"""Сборка финального черновика из data/book (база: v58 Claude pass)."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK_DIR = ROOT / "data" / "book"

# База: полный проход Claude (Jul 20) — лучше v59 в Части I
DEFAULT_BASE = BOOK_DIR / "НА_ПЕНСИЮ_НИКОГДА_v58_ЧАСТЬ_I_СВЕРЕНО.md"

_EDITORIAL_START = re.compile(
    r"^\s*>\s*\*\*🔧|^\s*>\s*\*\*Примечание к версии|РАЗМЕТКА АВТОРИТЕТОВ",
    re.I | re.M,
)


def _strip_editorial_preamble(text: str) -> str:
    """Убрать рабочие блоки в начале (🔧, примечание v51)."""
    lines = text.splitlines()
    out: list[str] = []
    skip_block = False
    for line in lines:
        if line.strip().startswith("> **🔧") or line.strip().startswith("> **Примечание к версии"):
            skip_block = True
            continue
        if skip_block:
            if line.strip() == "---" or (line.startswith("## ") and "СОДЕРЖАНИЕ" not in line):
                skip_block = False
                if line.strip() == "---":
                    continue
            else:
                continue
        out.append(line)
    return "\n".join(out)


def _clean_line(line: str) -> str:
    # Редакторские ⚠️ в квадратных скобках
    line = re.sub(r"\s*\[⚠️[^\]]*\]", "", line)
    # Отдельные строки-предупреждения italic
    if re.match(r"^\*⚠️.*\*$", line.strip()):
        return ""
    # HTML-комментарии и метки A/B
    line = re.sub(r"<!--.*?-->", "", line)
    line = re.sub(r"⟦[^⟧]*⟧", "", line)
    if "ВАРИАНТ A" in line or "ВАРИАНТ B" in line:
        return ""
    return line


def _mechanical_stoplist(text: str) -> str:
    """Безопасные замены (не трогаем канон «тихие кладбища»)."""
    # «вы» -> «ты» в типичных обращениях (осторожно)
    subs = (
        (r"\bвы наверняка\b", "ты наверняка"),
        (r"\bВы наверняка\b", "Ты наверняка"),
        (r"\bвы видели\b", "ты видел"),
        (r"\bВы видели\b", "Ты видел"),
        (r"\bвы горбатились\b", "ты горбатился"),
        (r"\bвам это продают\b", "тебе это продают"),
        (r"\bВам это продают\b", "Тебе это продают"),
        (r"\bвашей смерти\b", "твоей смерти"),
        (r"\bвстречали и сами\b", "встречал и сам"),
        (r"\b, просто (?!не\b)", ", "),
        (r"\bПросто (?!очень\b)", ""),
        (r"\b просто\b", ""),
        (r"\b ровно\b", ""),
        (r"\b потихоньку\b", " постепенно"),
        (r"\b по-тихому\b", " незаметно"),
        (r"\bИ вот что главное\.\s*", ""),
    )
    for pat, repl in subs:
        text = re.sub(pat, repl, text, flags=re.I if pat.islower() else 0)
    text = re.sub(r"  +", " ", text)
    text = re.sub(r" +\n", "\n", text)
    return text


def assemble(raw: str, *, version: str = "60") -> str:
    text = _strip_editorial_preamble(raw)
    lines = [_clean_line(ln) for ln in text.splitlines()]
    text = "\n".join(lines)
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Шапка версии
    text = re.sub(
        r"\*Версия \d+\*[^\n]*\n",
        f"*Черновик v{version} — сборка v58 Claude + вычистка разметки*\n",
        text,
        count=1,
    )
    return text.strip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--version", default="60")
    args = ap.parse_args()

    if not args.base.is_file():
        print(f"Missing base: {args.base}", file=sys.stderr)
        return 1

    out = args.output or BOOK_DIR / f"НА_ПЕНСИЮ_НИКОГДА_v{args.version}_ЧЕРНОВИК.md"
    raw = args.base.read_text(encoding="utf-8")
    result = assemble(raw, version=args.version)
    out.write_text(result, encoding="utf-8")
    also = ROOT / "data" / out.name
    if also != out:
        also.write_text(result, encoding="utf-8")

    print(f"Base:   {args.base} ({len(raw):,} chars)")
    print(f"Output: {out} ({len(result):,} chars)")
    print(f"Copy:   {also}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
