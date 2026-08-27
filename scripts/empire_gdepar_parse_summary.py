#!/usr/bin/env python3
"""Краткий отчёт по парсингу Где Пар (banya_spots / reviews / daily-лог)."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "empire.db"
DAILY_LOG = ROOT / "logs" / "banya_daily_last.log"


def build_gdepar_parse_summary(*, max_log_tail: int = 400) -> str:
    lines: list[str] = ["── Где Пар · парсинг ──"]
    if not DB.is_file():
        lines.append("❌ нет empire.db")
        return "\n".join(lines)

    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        pub = con.execute("SELECT COUNT(*) FROM banya_spots WHERE status='published'").fetchone()[0]
        draft = con.execute("SELECT COUNT(*) FROM banya_spots WHERE status='draft'").fetchone()[0]
        hidden = con.execute("SELECT COUNT(*) FROM banya_spots WHERE status='hidden'").fetchone()[0]
        ya = con.execute(
            "SELECT COUNT(*) FROM banya_spots "
            "WHERE yandex_url IS NOT NULL AND TRIM(yandex_url) != ''"
        ).fetchone()[0]
        regions = con.execute("SELECT COUNT(DISTINCT region) FROM banya_spots").fetchone()[0]
        rv_total = con.execute("SELECT COUNT(*) FROM banya_reviews").fetchone()[0]
        rv_ok = con.execute(
            "SELECT COUNT(*) FROM banya_reviews WHERE status='approved'"
        ).fetchone()[0]
        rv_pend = con.execute(
            "SELECT COUNT(*) FROM banya_reviews WHERE status='pending'"
        ).fetchone()[0]
        rv_1d = con.execute(
            "SELECT COUNT(*) FROM banya_reviews "
            "WHERE fetched_at >= datetime('now','-1 day')"
        ).fetchone()[0]
        updated_1d = con.execute(
            "SELECT COUNT(*) FROM banya_spots "
            "WHERE updated_at >= datetime('now','-1 day')"
        ).fetchone()[0]
        con.close()
    except Exception as exc:
        lines.append(f"❌ БД: {exc}")
        return "\n".join(lines)

    lines.append(f"точки: pub={pub} draft={draft} hidden={hidden} · регионов {regions}")
    lines.append(f"с Я.Картами: {ya} · обновлено за сутки: {updated_1d}")
    lines.append(f"отзывы: {rv_total} (ok={rv_ok} pending={rv_pend}) · +{rv_1d} за 24ч")

    if DAILY_LOG.is_file():
        try:
            body = DAILY_LOG.read_text(encoding="utf-8", errors="replace")
            started = re.search(r"# started:\s*(\S+)", body)
            rc_m = re.search(r"# rc:\s*(\S+)", body)
            saved = re.search(r"reviews done saved=(\d+).*?dup=(\d+).*?miss=(\d+)", body)
            moderate = "moderate-ai finished" in body or "moderate-ai:" in body
            mod_fail = "OpenRouter HTTP 403" in body or "moderate-ai finished rc=" in body and "rc=0" not in body
            head = "daily: "
            if started:
                head += started.group(1)[:19]
            if rc_m:
                head += f" rc={rc_m.group(1)}"
            lines.append(head)
            if saved:
                lines.append(
                    f"  отзывы сняты: +{saved.group(1)} dup={saved.group(2)} miss={saved.group(3)}"
                )
            if moderate:
                lines.append(
                    "  ИИ-модерация: ❌ OpenRouter 403"
                    if mod_fail and "OpenRouter HTTP 403" in body
                    else "  ИИ-модерация: была в прогоне"
                )
        except Exception as exc:
            lines.append(f"⚠ daily-лог: {exc}")
    else:
        lines.append("⚠ daily-лога нет (ночной прогон не писал)")

    return "\n".join(lines)


if __name__ == "__main__":
    print(build_gdepar_parse_summary())
