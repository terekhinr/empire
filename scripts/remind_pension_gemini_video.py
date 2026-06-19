#!/usr/bin/env python3
"""Отправить напоминание в Telegram (ADMIN_ID)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "pension" / "video" / "gemini_scheduled_report.txt"
FINAL = ROOT / "data" / "pension" / "video" / "pension_4scenes_gemini.mp4"


def send(text: str) -> bool:
    load_dotenv(ROOT / ".env")
    token = (os.getenv("TELEGRAM_TOKEN") or "").strip()
    admin = (os.getenv("ADMIN_ID") or "").strip()
    if not token or not admin:
        print("TELEGRAM_TOKEN или ADMIN_ID не задан", file=sys.stderr)
        return False
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": int(admin), "text": text, "parse_mode": "HTML"},
        timeout=30.0,
    )
    if r.status_code != 200:
        print(f"Telegram HTTP {r.status_code}: {r.text[:300]}", file=sys.stderr)
        return False
    return True


def _report_summary() -> str:
    if not REPORT.is_file():
        return "Отчёт ещё не создан — генерация, возможно, не запускалась."
    body = REPORT.read_text(encoding="utf-8", errors="replace").strip()
    lines = body.splitlines()[:8]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kind",
        choices=("done", "check"),
        default="check",
        help="done = после генерации; check = напоминание проверить",
    )
    args = parser.parse_args()

    if args.kind == "done":
        ok = FINAL.is_file() and FINAL.stat().st_size > 50000
        icon = "✅" if ok else "⚠️"
        text = (
            f"{icon} <b>Pension · Gemini Veo</b>\n"
            f"Генерация 4 сцен завершена.\n\n"
            f"<b>Проверьте видео:</b>\n"
            f"<code>{FINAL}</code>\n\n"
            f"{_report_summary()}"
        )
    else:
        text = (
            "⏰ <b>Напоминание</b>\n\n"
            "Проверьте видео «На пенсию НИКОГДА» (4 сцены, Gemini Veo):\n"
            f"• <code>{FINAL}</code>\n"
            f"• отчёт: <code>{REPORT}</code>\n\n"
            "Если файла нет — откройте лог <code>gemini_scheduled.log</code> "
            "(возможна квота 429 Veo)."
        )

    return 0 if send(text) else 1


if __name__ == "__main__":
    raise SystemExit(main())
