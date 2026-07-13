#!/usr/bin/env python3
"""Аудит реанимации каналов с опорой на литературу VPS → OpenRouter."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from evaluate_rag import openrouter_chat  # noqa: E402

OUT = ROOT / "docs/audit/literature_revival_audit_JUL2026.md"
PREV = ROOT / "docs/audit/openrouter_audit_RESPONSE_JUL2026.md"

MODELS = (
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.3-70b-instruct",
)


def _list_books(base: Path) -> list[str]:
    if not base.exists():
        return []
    out = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and p.suffix.lower() in {
            ".pdf", ".djvu", ".epub", ".fb2", ".doc", ".docx", ".txt", ".rag.txt"
        }:
            out.append(str(p.relative_to(ROOT)))
    return out


def build_inventory() -> str:
    manifests = {}
    for p in ROOT.glob("data/rag_manifest_*.json"):
        try:
            manifests[p.stem.replace("rag_manifest_", "")] = json.loads(p.read_text())
        except Exception:
            pass

    curated = {}
    for name in [
        "gdepar_classic_banya.json",
        "gdepar_duo_curated.json",
        "gdepar_book_excerpts.json",
        "stern_rubrics.json",
        "stern_curated.json",
        "stern_athletic_legacy.json",
        "garden_kizima_calendar.json",
        "lenin_rubrics.json",
        "lenin_bedtime_stories.json",
    ]:
        fp = ROOT / "data" / name
        if fp.exists():
            d = json.loads(fp.read_text(encoding="utf-8"))
            n = len(d.get("entries", d.get("posts", [])))
            if "rubrics" in d:
                curated[name] = {
                    k: len(v.get("entries", v.get("posts", [])))
                    for k, v in d["rubrics"].items()
                }
            else:
                curated[name] = n

    lines = ["## Инвентарь литературы VPS\n"]
    for persona in ("gdepar", "stern", "garden", "lenin", "pension"):
        m = manifests.get(persona, {})
        books = _list_books(ROOT / "data" / persona) + _list_books(ROOT / "kb_sources" / persona)
        lines.append(f"### {persona.upper()}")
        lines.append(f"- RAG chunks: {m.get('chunks', '?')}")
        lines.append(f"- Файлов книг: {len(books)}")
        for b in books[:25]:
            lines.append(f"  - {b}")
        if len(books) > 25:
            lines.append(f"  - … ещё {len(books)-25}")
        lines.append("")

    lines.append("## Curated JSON (уже в постах)\n")
    lines.append(json.dumps(curated, ensure_ascii=False, indent=2))
    return "\n".join(lines)


def build_prompt() -> str:
    prev = PREV.read_text(encoding="utf-8")[:12000] if PREV.exists() else ""
    inventory = build_inventory()
    rag_samples = (ROOT / "docs/audit/literature_rag_samples.txt").read_text(encoding="utf-8")[:8000] \
        if (ROOT / "docs/audit/literature_rag_samples.txt").exists() else ""

    return f"""Ты — главный редактор медиа-холдинга Empire (5 TG-каналов). Проведи АУДИТ РЕАНИМАЦИИ с опорой на реальную библиотеку на VPS.

Контекст предыдущего аудита (июль 2026):
{prev}

{inventory}

Примеры RAG-выдачи из книг (что реально лежит в индексе):
{rag_samples}

ЗАДАЧА — ответ на русском, структурированно:

1. **Карта «книга → тема поста»** — для каждого канала: какие книги на VPS НЕ используются в curated, но дают 5–10 сильных рубрик/серий. Конкретные названия книг и идеи постов (не абстракции).

2. **Что добавить к существующим слотам** — можно ли обогатить текущую матрицу (Gdepar 11/15/21, Stern 09:30/10/11/15/19, Garden 06:30/12/16/20, Lenin 08:30/12/19) цитатами/фактами из книг БЕЗ возврата к LLM-мусору? Какой формат: book_rubric JSON, цитата+комментарий, серия из N постов.

3. **Переработанные оценки каналов** (1–10) с учётом НЕИСПОЛЬЗОВАННОГО литературного потенциала.

4. **Матрица реанимации** — для каждого канала: ВЕРДИКТ (закрыть / заморозить / сократить / реанимировать / масштабировать), новая частота, какие слоты убрать, какие заменить book-driven curated.

5. **Перспективы на 3/6/12 мес** — реалистично, с метриками (подписчики, лиды, оплаты где уместно).

6. **Топ-10 быстрых wins** — что сделать за 1–2 недели (скрипты build_*_excerpts, импорт в JSON, без LLM).

7. **Риски** — авторские права на цитаты, медицинские дисклеймеры, McGill trademark.

Будь конкретен. Не предлагай «больше LLM». Предпочитай curated из книг.
"""


async def main() -> int:
    prompt = build_prompt()
    print(f"Prompt: {len(prompt):,} chars", file=sys.stderr)
    for model in MODELS:
        print(f"→ {model}", file=sys.stderr)
        status, content, data = await openrouter_chat(
            model, prompt, temperature=0.25, max_tokens=14000, timeout=300.0
        )
        if status == 200 and (content or "").strip():
            hdr = (
                f"# Empire · аудит реанимации (литература VPS)\n\n"
                f"**Модель:** `{model}`  \n"
                f"**Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n---\n\n"
            )
            OUT.write_text(hdr + content.strip() + "\n", encoding="utf-8")
            print(content)
            print(f"\n→ {OUT}", file=sys.stderr)
            return 0
        err = str(data.get("error", content))[:300]
        print(f"  fail {status}: {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
