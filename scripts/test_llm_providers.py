#!/usr/bin/env python3
"""Диагностика LLM: прямые API + OpenRouter. Показывает, что реально работает с VPS.

  ./venv/bin/python scripts/test_llm_providers.py
  ./venv/bin/python scripts/test_llm_providers.py --model openai/gpt-4o-mini
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from tools.llm_client import (  # noqa: E402
    JUDGE_FALLBACK_CHAIN,
    chat,
    openrouter_chat,
)

DEFAULT_MODELS = [
    "openai/gpt-4o-mini",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-flash",
    "deepseek/deepseek-v3.2",
    "qwen/qwen3-235b-a22b",
    "mistralai/mistral-small-3.1-24b-instruct",
]


def _keys_status() -> None:
    keys = {
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY"),
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
    }
    print("=== Ключи в .env ===")
    for k, v in keys.items():
        print(f"  {k}: {'✅ задан' if (v or '').strip() else '— нет'}")
    print()


async def _test_model(model: str) -> None:
    prompt = "Ответь одним словом: да"
    # direct path
    st_d, txt_d, data_d = await chat(model, prompt, max_tokens=20, prefer_direct=True)
    backend_d = (data_d or {}).get("backend", "?") if isinstance(data_d, dict) else "?"
    ok_d = st_d == 200 and (txt_d or "").strip() and not str(txt_d).startswith("{")
    print(f"{'✅' if ok_d else '❌'} {model}")
    print(f"   auto ({backend_d}): HTTP {st_d} | {(txt_d or _err(data_d))[:90]}")

    # openrouter only
    st_o, txt_o, data_o = await openrouter_chat(model, prompt, max_tokens=20)
    ok_o = st_o == 200 and (txt_o or "").strip() and not str(txt_o).startswith("{")
    print(f"   openrouter only: HTTP {st_o} | {(txt_o or _err(data_o))[:90]}")
    print()


def _err(data: dict | object) -> str:
    if isinstance(data, dict):
        e = data.get("error")
        if isinstance(e, dict):
            return str(e.get("message", e))[:120]
        return str(e or data)[:120]
    return str(data)[:120]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", help="проверить конкретную модель")
    args = ap.parse_args()
    models = args.model or DEFAULT_MODELS

    _keys_status()
    print("=== Тест моделей (auto = direct API → OpenRouter) ===\n")
    for m in models:
        await _test_model(m)

    print("=== Рекомендации ===")
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    has_gemini = bool(
        (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY") or "").strip()
    )
    if not has_openai:
        print("• GPT: добавьте OPENAI_API_KEY → platform.openai.com/api-keys")
    if not has_anthropic:
        print("• Claude: добавьте ANTHROPIC_API_KEY → console.anthropic.com")
    if has_gemini:
        print("• Gemini: ключ есть; при 429 включите billing в AI Studio")
    elif not has_gemini:
        print("• Gemini: добавьте GEMINI_API_KEY → aistudio.google.com/apikey")
    print("• OpenRouter 403 на GPT/Claude/Gemini = ограничение аккаунта OR, не VPS.")
    print("  Апелляция: https://forms.gle/yc2vyJiALz8Uhbmh7")
    print(f"• Рабочий fallback без frontier: {', '.join(JUDGE_FALLBACK_CHAIN[3:])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
