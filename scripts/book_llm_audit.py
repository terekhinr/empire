#!/usr/bin/env python3
"""Аудит главы через OpenRouter (Qwen) — только отчёт, без переписывания."""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tools.llm_client import chat

AUDIT_PROMPT = """Ты — редактор русского нон-фикшна. РЕЖИМ: только аудит, НЕ переписывай текст.

Проверь фрагмент по осям:
1. Стоп-слова: просто, ровно, вообще, именно, потихonьку (кроме «тихие кладбища»)
2. Конструкции «не X, а Y»
3. Тире-копула «это — то»
4. Обращение «вы» вместо «ты»
5. Канцелярит и «нейрослоп»
6. Маркеры 🔧 ⚠️ — должны быть удалены

Формат ответа:
## Найдено (до 15 пунктов)
| строка/абзац | цитата (до 15 слов) | проблема | предложение (1 фраза) |

Если чисто — напиши «Чисто по осям» и 1–2 сильные стороны.

ФРАГМЕНТ:
"""


def extract_chapter(text: str, chapter_num: int | None) -> str:
    if chapter_num is None:
        return text[:12000]
    pat = re.compile(rf"(##\s*Глава\s*{chapter_num}\b.*?)(?=##\s*Глава\s*\d+\b|\Z)", re.S | re.I)
    m = pat.search(text)
    if m:
        return m.group(1)[:25000]
    return text[:12000]


async def audit(path: Path, chapter: int | None, out: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    fragment = extract_chapter(raw, chapter)
    status, content, _ = await chat(
        "qwen/qwen3-235b-a22b",
        AUDIT_PROMPT + fragment,
        max_tokens=2048,
        temperature=0.1,
    )
    report = content if status == 200 else f"Ошибка LLM: HTTP {status}\n{_}"
    header = f"# Аудит Qwen3\n\n**Файл:** `{path.name}`\n**Глава:** {chapter or 'начало'}\n\n"
    out.write_text(header + report + "\n", encoding="utf-8")
    print(f"Report: {out} ({len(report)} chars)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manuscript", type=Path)
    ap.add_argument("--chapter", type=int, default=None)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()
    out = args.output or args.manuscript.with_name(
        args.manuscript.stem + f"_audit_ch{args.chapter or '0'}.md"
    )
    asyncio.run(audit(args.manuscript, args.chapter, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
