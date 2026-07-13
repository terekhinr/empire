#!/usr/bin/env python3
"""Генерация матриц постинга по каналам через OpenRouter (литература VPS)."""

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

OUT_DIR = ROOT / "docs"
MODEL = "deepseek/deepseek-chat"

CHANNELS = {
    "gdepar": {
        "out": "gdepar_posting_matrix_BOOKS_2026.md",
        "ctx": """
Канал: Gdepar (баня, gdepar.ru). 3 слота/день МСК: 11:00, 15:00, 21:00.
УЖЕ В КОДЕ (content_config.json): пн promo_map; вт book_rubric pechi_banya; ср-вс duo_curated practice/evening; чт вечер book_rubric istoriya_bani; 15:00 classic_banya (160 JSON).
Книги VPS: Хошев, Богданов СПб, Галицкий, Пустовойтов, Неумывакин, Микулин, Фальковский, Воеводина, Ушбаев.
Curated: classic 160, duo 139, book_excerpts растёт.
НЕ использовать LLM для 11/21 — только curated.
""",
    },
    "stern": {
        "out": "stern_posting_matrix_2026.md",
        "ctx": """
Канал: Stern / Снегири. 4 слота: 09:30 stern_curated, 10:00 stern_rubric, 15:00 stern_technique (сб видео), 19:00 stern_curated.
Убрать LLM 11:00 (ещё в старом конфиге не актуально — schedule 4 слота).
Книги VPS: Поляков/Воропаев 1988, Цацулин 2015, McGill, Майерс, Епифанов ЛФК, Фицджеральд, Ильин, Мохан, «Приросший к стулу», Маматов.
Rubrics: kettlebell_history 5, russian_strongmen 4, sports_med 4, equipment 4, kettlebell_fitness 4.
athletic_legacy 301, stern_curated 151.
McGill — без trademark в тексте. Дисклеймер медицина.
""",
    },
    "garden": {
        "out": "garden_posting_matrix_CURATED_2026.md",
        "ctx": """
Канал: Garden. РЕЖИМ ЗАМОРОЗКИ: persona disabled, было 4/день LLM-спам.
Якорь: 20:00 kizima_lunar (381 день JSON).
Книги VPS: Кизима 6+, Курдюмов 3, Воробьев теплицы, Петросян удобрения, Завязкин консервирование, Миттлайдер.
Цель: 1 пост/нед (луна) + опционально 1 curated/мес из Курдюмова.
НЕ «План на день» LLM.
""",
    },
    "lenin": {
        "out": "lenin_posting_matrix_2026.md",
        "ctx": """
Канал: Lenin. 3 слота: 08:30 lenin_calendar (prebuilt), 12:00 lenin_rubric (JSON), 19:00 pss/book/marxism/support.
ПСС 45 томов в RAG. Rubrics: literature 11, art 4, biography 71, cinema 5. Bedtime 245.
Без llm_free. Вечер: PSS curated из RAG без LLM где возможно.
""",
    },
    "pension": {
        "out": "pension_posting_matrix_2026.md",
        "ctx": """
Канал: Pension / neverretire. Автопост выкл. Книга launch сентябрь 2026.
Crimson RAG 24 файла. book_complete.md для YT/книги.
Ручной режим: 1 пост/нед до launch. Темы из глав книги + 1 факт Crimson/мес.
""",
    },
}


def prompt_for(channel: str, ctx: str) -> str:
    return f"""Ты — редактор Empire. Напиши ГОТОВУЮ МАТРИЦУ ПОСТИНГА для канала {channel.upper()}.

{ctx}

Формат как у «Классическая баня» Gdepar и Lenin — таблицы по дням недели, слоты МСК, тип контента (curated/book/duo/video), источник JSON/книга, риски, визуал.

Обязательные разделы:
## 1. Ритм и слоты (таблица)
## 2. Матрица по дням недели (пн-вс × слоты) — конкретные темы/рубрики/книги
## 3. Книги VPS → рубрики (таблица: книга | серия | слот | сколько постов | JSON файл)
## 4. Ротация и анти-повторы (cooldown, пулы)
## 5. Визуал (Commons / свои / Fal prompt шаблон)
## 6. Чеклист редактора
## 7. Следующий шаг в репо (какие JSON править)

Без LLM-мусора. Только curated. Русский язык. Конкретика: названия книг, id рубрик, имена файлов data/*.json.
Длина: полная матрица на 2-4 экрана.
"""


async def main() -> int:
    for ch, meta in CHANNELS.items():
        print(f"=== {ch} ===", file=sys.stderr)
        status, content, data = await openrouter_chat(
            MODEL,
            prompt_for(ch, meta["ctx"]),
            temperature=0.3,
            max_tokens=6000,
            timeout=180.0,
        )
        if status != 200 or not (content or "").strip():
            print(f"FAIL {ch}: {data.get('error')}", file=sys.stderr)
            continue
        out = OUT_DIR / meta["out"]
        hdr = (
            f"# {ch.title()} TG · матрица постинга 2026\n\n"
            f"**Сгенерировано:** OpenRouter `{MODEL}` · "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  \n"
            f"**Режим:** curated / книги VPS, без LLM-мусора  \n"
            f"**Код:** `content_config.json` → `{ch}`\n\n---\n\n"
        )
        out.write_text(hdr + content.strip() + "\n", encoding="utf-8")
        print(f"OK → {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
