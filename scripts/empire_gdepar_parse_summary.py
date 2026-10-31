#!/usr/bin/env python3
"""Краткий отчёт по парсингу Где Пар (banya_spots / reviews).

Используется в empire-weekly-report (раз в неделю). Не для daily digest.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "empire.db"
WEEKLY_LOG = ROOT / "logs" / "banya_weekly.log"
DAILY_LOG = ROOT / "logs" / "banya_daily_last.log"  # legacy
FLAGSHIP = ("MSK", "MO", "SPB", "LO")


def build_gdepar_parse_summary(*, max_log_tail: int = 400) -> str:
    lines: list[str] = ["── Где Пар · каталог (неделя) ──"]
    if not DB.is_file():
        lines.append("❌ нет empire.db")
        return "\n".join(lines)

    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        pub = con.execute("SELECT COUNT(*) FROM banya_spots WHERE status='published'").fetchone()[0]
        draft = con.execute("SELECT COUNT(*) FROM banya_spots WHERE status='draft'").fetchone()[0]
        hidden = con.execute("SELECT COUNT(*) FROM banya_spots WHERE status='hidden'").fetchone()[0]
        ph = ",".join("?" * len(FLAGSHIP))
        flag_pub = con.execute(
            f"SELECT COUNT(*) FROM banya_spots WHERE status='published' AND region IN ({ph})",
            FLAGSHIP,
        ).fetchone()[0]
        quality = con.execute(
            f"SELECT COUNT(*) FROM banya_spots WHERE status='published' AND region IN ({ph}) "
            "AND COALESCE(reviews_total,0) >= 50 "
            "AND phone IS NOT NULL AND TRIM(phone) != ''",
            FLAGSHIP,
        ).fetchone()[0]
        ya = con.execute(
            "SELECT COUNT(*) FROM banya_spots "
            "WHERE yandex_url IS NOT NULL AND TRIM(yandex_url) != ''"
        ).fetchone()[0]
        rv_total = con.execute("SELECT COUNT(*) FROM banya_reviews").fetchone()[0]
        rv_ok = con.execute(
            "SELECT COUNT(*) FROM banya_reviews WHERE status='approved'"
        ).fetchone()[0]
        rv_pend = con.execute(
            "SELECT COUNT(*) FROM banya_reviews WHERE status='pending'"
        ).fetchone()[0]
        rv_7d = con.execute(
            "SELECT COUNT(*) FROM banya_reviews "
            "WHERE fetched_at >= datetime('now','-7 day')"
        ).fetchone()[0]
        updated_7d = con.execute(
            "SELECT COUNT(*) FROM banya_spots "
            "WHERE updated_at >= datetime('now','-7 day')"
        ).fetchone()[0]
        con.close()
    except Exception as exc:
        lines.append(f"❌ БД: {exc}")
        return "\n".join(lines)

    lines.append(f"все: pub={pub} draft={draft} hidden={hidden}")
    lines.append(
        f"FLAGSHIP published={flag_pub} · quality(≥50 отз+тел)={quality} · Я.URL={ya}"
    )
    lines.append(
        f"обновлено за 7д: {updated_7d} · отзывы +{rv_7d}/нед "
        f"(всего {rv_total}, ok={rv_ok}, pend={rv_pend})"
    )

    log_path = WEEKLY_LOG if WEEKLY_LOG.is_file() else DAILY_LOG
    if log_path.is_file():
        try:
            body = log_path.read_text(encoding="utf-8", errors="replace")
            started = re.search(r"(?:BANYA WEEKLY START|# started:)\s*(\S+)", body)
            low = sum(1 for _ in re.finditer(r"low_traffic→draft", body))
            lines.append(
                f"лог {log_path.name}: "
                + (started.group(1)[:19] if started else "есть")
                + (f" · low_traffic demote≈{low}" if low else "")
            )
        except Exception as exc:
            lines.append(f"⚠ лог: {exc}")
    else:
        lines.append("⚠ weekly-лога ещё нет (первый прогон в вс)")

    return "\n".join(lines)


if __name__ == "__main__":
    print(build_gdepar_parse_summary())
