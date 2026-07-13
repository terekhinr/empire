#!/usr/bin/env python3
"""Прогон сессий Снегири 0/A/B через OpenRouter (дешёвые модели).

Пример:
  ./venv/bin/python scripts/run_snegiri_openrouter_sessions.py
  ./venv/bin/python scripts/run_snegiri_openrouter_sessions.py --session 0
  ./venv/bin/python scripts/run_snegiri_openrouter_sessions.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
load_dotenv("/etc/empire/empire.env")

from evaluate_rag import openrouter_chat  # noqa: E402

# import extract_session_prompt from sibling script
import importlib.util

_gspec = importlib.util.spec_from_file_location(
    "gemini_session", ROOT / "scripts" / "gemini_session.py"
)
_gmod = importlib.util.module_from_spec(_gspec)
_gspec.loader.exec_module(_gmod)
extract_session_prompt = _gmod.extract_session_prompt

MASTER = ROOT / "docs" / "snegiri_gemini_master_sessions.md"

# Работают с этого VPS (Google/OpenAI = 403 ToS). Приоритет: цена + качество RU.
MODEL_CANDIDATES = [
    "deepseek/deepseek-chat",              # ~$0.14/1M in — основная
    "qwen/qwen-2.5-72b-instruct",        # сильнее на длинных отчётах
    "mistralai/mistral-small-3.1-24b-instruct",
    "qwen/qwen-2.5-7b-instruct",         # дешевле всех
    "meta-llama/llama-3.1-8b-instruct",
]

SESSION_ATTACH = {
    "A": [ROOT / "docs/snegiri_product_prelaunch_methodology.md"],
    "B": [
        ROOT / "docs/snegiri_finmodel_v4.md",
        ROOT / "docs/snegiri_finmodel_v3.md",
    ],
}

OUT_MAP = {
    "0": ROOT / "docs/snegiri_openrouter_session_0_audit.md",
    "A": ROOT / "docs/snegiri_openrouter_session_A_prelaunch.md",
    "B": ROOT / "docs/snegiri_openrouter_session_B_finmodel.md",
    "J": ROOT / "docs/snegiri_openrouter_session_J_comic_failure.md",
}

META_PATH = ROOT / "docs/snegiri_openrouter_sessions_meta.json"


def read_attachments(paths: list[Path], limit: int = 25_000) -> str:
    chunks: list[str] = []
    for p in paths:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        if len(text) > limit:
            text = text[:limit] + f"\n\n[обрезано до {limit} символов]"
        chunks.append(f"\n\n---\n# ПРИЛОЖЕНИЕ: {p.name}\n\n{text}")
    return "".join(chunks)


def build_prompt(session_id: str) -> str:
    master = MASTER.read_text(encoding="utf-8")
    prompt = extract_session_prompt(master, session_id)
    attach = SESSION_ATTACH.get(session_id.upper(), [])
    if attach:
        prompt += read_attachments(attach)
    prompt += (
        "\n\n---\n"
        "КОНТЕКСТ: ответ Cursor уже в docs/snegiri_gemini_session_*.md — "
        "сделай независимый аудит, оспорь слабое, дополни. "
        "Русский язык. Markdown. Без воды."
    )
    return prompt


async def call_with_fallback(prompt: str, max_tokens: int) -> tuple[str, str, dict]:
    last = ""
    for model in MODEL_CANDIDATES:
        print(f"  → {model} …", file=sys.stderr, flush=True)
        status, content, data = await openrouter_chat(
            model,
            prompt,
            temperature=0.3,
            max_tokens=max_tokens,
            timeout=240.0,
        )
        if status == 200 and content.strip():
            return model, content.strip(), data
        err = data.get("error") if isinstance(data, dict) else content
        last = f"{model}: HTTP {status} — {str(err)[:200]}"
        print(f"    fail: {last}", file=sys.stderr)
    raise SystemExit(f"Все модели отказали. Последняя: {last}")


def write_out(path: Path, session: str, model: str, content: str, usage: dict | None) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    usage_s = ""
    if usage:
        usage_s = f"\n**Токены:** `{json.dumps(usage, ensure_ascii=False)}`"
    header = (
        f"# OpenRouter · Сессия {session}\n\n"
        f"**Дата:** {ts}  \n"
        f"**Модель:** `{model}`  \n"
        f"**Провайдер:** [OpenRouter](https://openrouter.ai){usage_s}\n\n---\n\n"
    )
    path.write_text(header + content + "\n", encoding="utf-8")
    print(f"OK → {path} ({len(content):,} символов)", file=sys.stderr)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", choices=["0", "A", "B", "J", "all"], default="all")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-tokens", type=int, default=8000)
    args = ap.parse_args()

    if not os.getenv("OPENROUTER_API_KEY", "").strip():
        print("OPENROUTER_API_KEY не задан в .env", file=sys.stderr)
        return 1

    sessions = ["0", "A", "B", "J"] if args.session == "all" else [args.session.upper()]

    meta: dict = {"runs": [], "ts": datetime.now(timezone.utc).isoformat()}

    for sid in sessions:
        print(f"\n=== Сессия {sid} ===", file=sys.stderr)
        prompt = build_prompt(sid)
        print(f"Промпт: {len(prompt):,} символов", file=sys.stderr)
        if args.dry_run:
            print(prompt[:500] + "…", file=sys.stderr)
            continue

        model, content, data = await call_with_fallback(prompt, args.max_tokens)
        out = OUT_MAP[sid]
        usage = data.get("usage") if isinstance(data, dict) else None
        write_out(out, sid, model, content, usage)
        meta["runs"].append(
            {
                "session": sid,
                "model": model,
                "out": str(out.relative_to(ROOT)),
                "prompt_chars": len(prompt),
                "response_chars": len(content),
                "usage": usage,
            }
        )

    if not args.dry_run:
        META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nMeta → {META_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
