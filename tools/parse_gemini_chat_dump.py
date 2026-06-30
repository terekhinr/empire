#!/usr/bin/env python3
"""Извлечь посты id: duo_* из дампа чата Gemini (с UI-мусором)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "docs" / "content_factory" / "gemini_export"

SKIP_PREFIXES = (
    "Режим чтения",
    "Увеличить",
    "Уменьшить",
    "Фон",
    "Шрифт",
    "Выйти",
    "Google Gemini",
    "Ваш запрос",
    "Фото профиля",
    "продолжаем",
    "продолжай",
    "дальше",
    "сохраняй",
)

FM_KEYS = ("id", "pool", "slot", "tag", "headline", "hashtags", "image_file")


def _clean(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            lines.append("")
            continue
        if s.startswith("# ЗАДАНИЕ"):
            break
        if s.startswith("## CHECKLIST") or s == "CHECKLIST":
            break
        if s.startswith("POST_COUNT:") or s.startswith("P0_FOUND:") or s.startswith("IDS:"):
            break
        if any(s.startswith(p) for p in SKIP_PREFIXES):
            continue
        if s.startswith("- `GDP-"):
            continue
        if s.startswith("УЖЕ ЕСТЬ") or s.startswith("Формат поста"):
            continue
        if s.startswith("Правила из") or s.startswith("Имя файла"):
            continue
        if s.startswith("```"):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def extract_posts(text: str) -> list[str]:
    parts = re.split(r"\n(?=id:\s*duo_)", text, flags=re.IGNORECASE)
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        part = part.strip()
        if not part.lower().startswith("id:"):
            continue
        m = re.match(r"^id:\s*(\S+)", part, re.I)
        if not m:
            continue
        pid = m.group(1).strip("`")
        if pid in seen:
            continue
        seen.add(pid)
        cleaned = _clean(part)
        if not cleaned:
            continue
        out.append(cleaned)
    return out


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not src or not src.is_file():
        print("usage: parse_gemini_chat_dump.py <chat_dump.txt>")
        return 1
    raw = src.read_text(encoding="utf-8", errors="replace")
    posts = extract_posts(raw)
    if not posts:
        print("ERROR: 0 posts")
        return 1
    out = EXPORT / "gemini-code-gdepar_bulk_03_12.md"
    out.write_text("\n\n".join(posts) + "\n", encoding="utf-8")
    print(f"OK {len(posts)} unique posts → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
