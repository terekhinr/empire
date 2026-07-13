#!/usr/bin/env python3
"""Полный аудит TG-каналов Empire через OpenRouter (Claude/Gemini)."""

from __future__ import annotations

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

from evaluate_rag import openrouter_chat  # noqa: E402

AUDIT_DIR = ROOT / "docs" / "audit"
EXPORT = AUDIT_DIR / "gemini_export"
OUT_PATH = AUDIT_DIR / "openrouter_audit_RESPONSE_JUL2026.md"

MODELS = (
    "deepseek/deepseek-chat",
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-4-maverick",
)


def _read(name: str, limit: int | None = None) -> str:
    p = EXPORT / name if (EXPORT / name).exists() else AUDIT_DIR / name
    if not p.exists():
        return f"[файл {name} отсутствует]"
    text = p.read_text(encoding="utf-8", errors="replace")
    if limit and len(text) > limit:
        return text[:limit] + f"\n\n… [обрезано, всего {len(text)} символов]"
    return text


def build_prompt() -> str:
    prompt_tpl = (AUDIT_DIR / "gemini_PROMPT_FULL_AUDIT_JUL2026.txt").read_text(encoding="utf-8")
    channel_ctx = _read("channel_context.md")
    stats = _read("full_audit_stats.json")
    flags = _read("pattern_flags.tsv")
    stats_tsv = _read("stats_summary.tsv")
    backlog = _read("backlog_summary.tsv")
    samples = _read("audit_samples_good_vs_bad.txt")
    last40 = _read("all_channels_last40.txt", limit=70_000)
    topics = _read("topics_distribution.tsv", limit=25_000)

    snegiri_brief = ""
    for extra in (
        ROOT / "docs/snegiri_self_audit_2026-07-13.md",
        ROOT / "docs/snegiri_gemini_session_0_audit.md",
    ):
        if extra.is_file():
            snegiri_brief += f"\n\n### {extra.name}\n" + extra.read_text(encoding="utf-8")[:4000]

    playbook = ""
    pb = ROOT / "docs/EMPIRE_PIPELINE_PLAYBOOK_RU.md"
    if pb.is_file():
        playbook = pb.read_text(encoding="utf-8")[:6000]

    return f"""{prompt_tpl}

═══════════════════════════════════════
ДАННЫЕ (приложены ниже)
═══════════════════════════════════════

## channel_context.md
{channel_ctx}

## stats_summary.tsv
{stats_tsv}

## pattern_flags.tsv
{flags}

## backlog_summary.tsv
{backlog}

## full_audit_stats.json
{stats}

## topics_distribution.tsv (топ повторов)
{topics}

## audit_samples_good_vs_bad.txt
{samples}

## all_channels_last40.txt
{last40}

## Empire playbook (фрагмент — бизнес-цели)
{playbook}

## Снегири / Stern продукт (фрагмент)
{snegiri_brief}

Дополнительно: учти что pension (14 постов) владелец ведёт сам — 1 абзац.
Ответ на русском. Будь жёстким. В конце — таблица решений по каждому проекту с метриками на 3/6/12 мес.
"""


async def main() -> int:
    prompt = build_prompt()
    print(f"Prompt size: {len(prompt):,} chars", file=sys.stderr)

    last_err = ""
    for model in MODELS:
        print(f"Calling {model}…", file=sys.stderr)
        status, content, data = await openrouter_chat(
            model,
            prompt,
            temperature=0.2,
            max_tokens=12000,
            timeout=300.0,
        )
        if status == 200 and content.strip():
            header = (
                f"# Empire · аудит каналов (OpenRouter)\n\n"
                f"**Модель:** `{model}`  \n"
                f"**Дата:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  \n"
                f"**Корпус:** 828 published постов (2026-05-07 … 2026-07-13)\n\n"
                f"---\n\n"
            )
            OUT_PATH.write_text(header + content.strip() + "\n", encoding="utf-8")
            meta = {
                "model": model,
                "prompt_chars": len(prompt),
                "response_chars": len(content),
                "usage": data.get("usage"),
            }
            (AUDIT_DIR / "openrouter_audit_meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(content)
            print(f"\nOK → {OUT_PATH}", file=sys.stderr)
            return 0
        last_err = str(data.get("error") or content or data)[:500]
        print(f"  fail {status}: {last_err}", file=sys.stderr)

    print(f"All models failed: {last_err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
