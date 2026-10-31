"""ИИ-фабрика черновиков для банка (только в админке, не в момент публикации)."""

from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

PERSONA_HINTS: dict[str, str] = {
    "gdepar": "Канал про русскую баню: практика, культура, без рекламного крика. Тон спокойный, конкретный.",
    "pension": "Канал «На пенсию никогда»: деньги, работа после 50, без пафоса и страшилок.",
    "stern": "Канал про гиревой спорт и ОФП: техника, здоровье, без допинг-бреда.",
    "lenin": "Канал про Ленина в культуре/истории: факты и цитаты, без троллинга.",
    "garden": "Канал про сад/огород по Кизиме и практике: сезонно, по делу.",
}


def _default_model() -> str:
    return (
        os.getenv("EMPIRE_STUDIO_AI_MODEL")
        or os.getenv("OPENROUTER_MODEL")
        or "deepseek/deepseek-chat"
    ).strip()


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return []
    # вырезать ```json ... ```
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # попытка найти массив
        m = re.search(r"\[[\s\S]*\]", raw)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("headline") or "").strip()
        body = str(item.get("body") or item.get("text") or "").strip()
        if not body:
            continue
        out.append(
            {
                "title": title or body.split("\n", 1)[0][:80],
                "body": body,
                "category": str(item.get("category") or "general").strip() or "general",
            }
        )
    return out


async def generate_drafts_async(
    *,
    persona: str,
    rubric: str,
    count: int = 5,
    extra: str = "",
) -> tuple[list[dict[str, Any]], str]:
    """Вернуть (drafts, error). error пуст при успехе."""
    from tools.llm_client import openrouter_chat

    n = max(1, min(int(count or 5), 15))
    hint = PERSONA_HINTS.get(persona, "Тематический Telegram-канал.")
    system = (
        "Ты редактор Telegram-канала. Пиши по-русски. "
        "Верни ТОЛЬКО JSON-массив объектов "
        '[{"title":"...","body":"...","category":"..."}]. '
        "Без markdown вне JSON. Каждый body 400–900 символов, конкретика, без воды и без хештег-спама."
    )
    user = (
        f"Персона/канал: {persona}\n"
        f"Контекст: {hint}\n"
        f"Рубрика: {rubric or 'общая'}\n"
        f"Сделай {n} черновиков постов.\n"
        f"{extra.strip()}"
    )
    status, content, meta = await openrouter_chat(
        _default_model(),
        user,
        system_prompt=system,
        temperature=0.7,
        max_tokens=4096,
        title="Empire Ops Studio",
    )
    if status == 0:
        return [], str((meta or {}).get("error") or "no_openrouter_key")
    if status >= 400:
        return [], f"openrouter_http_{status}"
    drafts = _parse_json_array(content or "")
    if not drafts:
        return [], "parse_failed"
    return drafts[:n], ""


def generate_drafts(
    *,
    persona: str,
    rubric: str,
    count: int = 5,
    extra: str = "",
) -> tuple[list[dict[str, Any]], str]:
    return asyncio.run(
        generate_drafts_async(persona=persona, rubric=rubric, count=count, extra=extra)
    )
