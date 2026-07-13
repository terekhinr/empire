#!/usr/bin/env python3
"""Еженедельный аудит качества постов → Telegram + лог. Вс 09:00 МСК (после техотчёта)."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import content_audit as ca  # noqa: E402
import empire_notify as notify  # noqa: E402

LOG_DIR = Path(os.getenv("EMPIRE_LOG_DIR", "/var/log/empire"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Еженедельный аудит контента Empire")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--db", default=str(ROOT / "empire.db"))
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument(
        "--reject-junk",
        action="store_true",
        help="Отклонить pending с Свободная тема / P0 / старый LLM-мусор",
    )
    ap.add_argument("--apply-reject", action="store_true", help="С --reject-junk: записать в БД")
    args = ap.parse_args()

    report = ca.build_audit_report(Path(args.db), days=args.days)

    if args.reject_junk:
        ids = ca.reject_junk_pending(
            Path(args.db),
            dry_run=not args.apply_reject,
        )
        mode = "отклонено" if args.apply_reject else "к отклонению (dry-run)"
        report += f"\n\n── Junk pending ({mode}): {len(ids)} ──\n"
        for i in ids[:15]:
            report += f"  · #{i}\n"
        if len(ids) > 15:
            report += f"  … и ещё {len(ids) - 15}\n"

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = LOG_DIR / f"content-audit-{stamp}.txt"
    path.write_text(report, encoding="utf-8")
    (LOG_DIR / "content-audit-latest.txt").write_text(report, encoding="utf-8")
    print(report)

    if args.no_telegram:
        return 0
    max_len = int(os.getenv("EMPIRE_AUDIT_TELEGRAM_MAX", "3900"))
    text = report if len(report) <= max_len else report[: max_len - 20] + "\n… (обрезано)"
    return 0 if notify.send(text) else 1


if __name__ == "__main__":
    raise SystemExit(main())
