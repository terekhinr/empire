#!/usr/bin/env python3
"""Telegram-отчёт empire_daily_audit.sh (через empire_notify)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import empire_notify as notify  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True)
    parser.add_argument("--issues", type=int, required=True)
    parser.add_argument("--warnings", type=int, required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("lines", nargs="*", default=[])
    args = parser.parse_args()

    icon = {"OK": "✅", "WARN": "⚠️", "ISSUES": "🚨"}.get(args.status, "ℹ️")
    host = os.uname().nodename
    header = (
        f"{icon} Empire audit · {host}\n"
        f"Статус: {args.status} · проблем: {args.issues} · предупреждений: {args.warnings}\n"
    )
    body = "\n".join(args.lines[:25]) if args.lines else "(детали в логе на VPS)"
    footer = f"\n\n📄 {args.report}"
    text = header + body + footer
    max_len = int(os.getenv("EMPIRE_AUDIT_TELEGRAM_MAX", "3500"))
    if len(text) > max_len:
        text = text[: max_len - 20] + "\n… (обрезано)"
    key = f"audit:{args.status}:{args.issues}:{args.warnings}"
    ok = notify.send_if_changed(key, text, min_interval_sec=1800) or notify.send(text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
