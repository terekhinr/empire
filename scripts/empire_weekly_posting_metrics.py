#!/usr/bin/env python3
"""Еженедельные метрики постинга: autopublish, очередь, эффективность по персонам.

Пишет data/empire_weekly_kpi.json и лог /var/log/empire/posting-metrics-latest.json
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = Path(os.getenv("EMPIRE_LOG_DIR", "/var/log/empire"))
DB = Path(os.getenv("EMPIRE_DB", str(ROOT / "empire.db")))
KPI_PATH = ROOT / "data" / "empire_weekly_kpi.json"
DAYS = int(os.getenv("EMPIRE_POSTING_METRICS_DAYS", "7"))


def journal_autopublish(days: int) -> dict:
    since = f"{days} days ago"
    try:
        r = subprocess.run(
            ["journalctl", "-u", "empire_main", "--since", since, "--no-pager"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        text = r.stdout or ""
    except Exception as exc:
        return {"error": str(exc), "published": 0, "skip": 0, "by_persona": {}}

    pub_re = re.compile(r"\[autopublish\] published #\d+ (\w+)")
    skip_re = re.compile(r"\[autopublish\] skip #\d+ (\w+): (.+)")
    by_persona: dict[str, dict] = defaultdict(lambda: {"published": 0, "skip": 0, "skip_reasons": Counter()})

    for m in pub_re.finditer(text):
        by_persona[m.group(1)]["published"] += 1
    for m in skip_re.finditer(text):
        p, reason = m.group(1), m.group(2)[:80]
        by_persona[p]["skip"] += 1
        by_persona[p]["skip_reasons"][reason] += 1

    published = sum(v["published"] for v in by_persona.values())
    skip = sum(v["skip"] for v in by_persona.values())
    # serialize counters
    out_persona = {}
    for p, v in by_persona.items():
        out_persona[p] = {
            "published": v["published"],
            "skip": v["skip"],
            "success_rate": round(v["published"] / max(1, v["published"] + v["skip"]), 3),
            "top_skip_reasons": dict(v["skip_reasons"].most_common(3)),
        }
    return {
        "published": published,
        "skip": skip,
        "success_rate": round(published / max(1, published + skip), 3),
        "by_persona": out_persona,
    }


def db_queue_stats() -> dict:
    if not DB.is_file():
        return {"error": "no empire.db"}
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=DAYS)).isoformat()
        cur = conn.execute(
            """
            SELECT persona_key, status, COUNT(*) AS n
            FROM post_drafts
            GROUP BY persona_key, status
            """
        )
        by_status: dict[str, dict] = defaultdict(dict)
        for row in cur:
            by_status[row["persona_key"]][row["status"]] = row["n"]

        cur2 = conn.execute(
            """
            SELECT persona_key, COUNT(*) AS n
            FROM post_drafts
            WHERE status IN ('draft', 'pending', 'hidden')
            GROUP BY persona_key
            """
        )
        queue = {row["persona_key"]: row["n"] for row in cur2}

        cur3 = conn.execute(
            """
            SELECT persona_key, COUNT(*) AS n
            FROM post_drafts
            WHERE status = 'published' AND created_at >= ?
            GROUP BY persona_key
            """,
            (since,),
        )
        published_week = {row["persona_key"]: row["n"] for row in cur3}
    except sqlite3.Error as exc:
        return {"error": str(exc)}
    finally:
        conn.close()

    return {
        "queue_pending_by_persona": queue,
        "published_in_db_week": published_week,
        "status_breakdown": dict(by_status),
    }


def load_finance_weekly_expenses() -> float | None:
    ledger = ROOT / "data" / "empire_finance_ledger.json"
    if not ledger.is_file():
        return None
    try:
        data = json.loads(ledger.read_text(encoding="utf-8"))
        entries = data.get("entries") or []
        since = datetime.now(timezone.utc) - timedelta(days=DAYS)
        total = 0.0
        for e in entries:
            if e.get("type") != "expense":
                continue
            try:
                dt = datetime.fromisoformat(e["date"])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if dt >= since:
                total += float(e.get("amount_rub") or 0)
        return round(total, 2)
    except Exception:
        return None


def week_start_iso() -> str:
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.strftime("%Y-%m-%d")


def build_report() -> tuple[dict, str]:
    autop = journal_autopublish(DAYS)
    db = db_queue_stats()
    expenses = load_finance_weekly_expenses()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "week": week_start_iso(),
        "period_days": DAYS,
        "autopublish": autop,
        "database": db,
        "kpi": {
            "tg_posts_published": autop.get("published", 0),
            "autopost_failures": autop.get("skip", 0),
            "autopost_success_rate": autop.get("success_rate", 0),
            "expenses_rub_week": expenses,
            "revenue_rub": 0,
            "orders": 0,
            "empire_ok": 1 if autop.get("skip", 0) == 0 else 0,
        },
        "efficiency_notes": [],
    }

    # Оценка эффективности
    notes = []
    sr = autop.get("success_rate", 0)
    if sr >= 0.95:
        notes.append("Автопост стабилен (≥95% слотов)")
    elif sr >= 0.8:
        notes.append("Автопост приемлемый; проверьте skip_reasons")
    else:
        notes.append("⚠ Много skip — пополните queue или ослабьте curated-only")

    for p, info in (autop.get("by_persona") or {}).items():
        if info.get("published", 0) == 0 and info.get("skip", 0) > 0:
            notes.append(f"{p}: 0 публикаций за неделю — пустая очередь?")

    empty_queue = [p for p, n in (db.get("queue_pending_by_persona") or {}).items() if n < 2]
    if empty_queue:
        notes.append(f"Мало черновиков: {', '.join(empty_queue)}")

    payload["efficiency_notes"] = notes

    lines = [
        f"📈 Постинг · неделя с {week_start_iso()}",
        f"Опубликовано: {autop.get('published', 0)} · skip: {autop.get('skip', 0)} "
        f"· success {autop.get('success_rate', 0):.0%}",
        "",
        "── По персонам ──",
    ]
    for p, info in sorted((autop.get("by_persona") or {}).items()):
        lines.append(
            f"  {p}: +{info.get('published', 0)} skip={info.get('skip', 0)} "
            f"({info.get('success_rate', 0):.0%})"
        )
    if notes:
        lines.extend(["", "── Оценка ──", *[f"• {n}" for n in notes]])
    lines.append("")
    lines.append(f"JSON: {KPI_PATH}")

    return payload, "\n".join(lines)


def main() -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    import empire_notify as notify  # noqa: E402

    payload, text = build_report()
    KPI_PATH.parent.mkdir(parents=True, exist_ok=True)

    # merge into kpi file (list of weeks)
    history: list = []
    if KPI_PATH.is_file():
        try:
            history = json.loads(KPI_PATH.read_text(encoding="utf-8"))
            if isinstance(history, dict):
                history = [history]
        except Exception:
            history = []
    # replace same week
    history = [h for h in history if h.get("week") != payload["week"]]
    history.append(payload)
    history.sort(key=lambda x: x.get("week", ""))
    KPI_PATH.write_text(json.dumps(history[-52:], ensure_ascii=False, indent=2), encoding="utf-8")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    latest = LOG_DIR / "posting-metrics-latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (LOG_DIR / "posting-metrics-latest.txt").write_text(text, encoding="utf-8")

    # Копии для IDE (data/ может быть тяжёлым; docs/ — всегда копируемо)
    export_dir = ROOT / "docs" / "audit" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "empire_weekly_kpi.json").write_text(
        json.dumps(history[-52:], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (export_dir / "posting-metrics-latest.txt").write_text(text, encoding="utf-8")

    # Яндекс.Диск — только из morning-brief / export_audit_to_yandex (не рекурсить отсюда).
    sync_sh = ROOT / "scripts" / "export_audit_to_yandex.sh"
    if (
        sync_sh.is_file()
        and os.getenv("EMPIRE_SKIP_YANDEX_AUDIT") != "1"
        and os.getenv("EMPIRE_POSTING_METRICS_NO_TELEGRAM") != "1"
    ):
        try:
            subprocess.run(["bash", str(sync_sh)], cwd=str(ROOT), timeout=300, check=False)
        except Exception:
            pass

    print(text)
    # TG только по явному флагу (systemd timer / ручной запуск с TELEGRAM=1).
    if os.getenv("EMPIRE_POSTING_METRICS_TELEGRAM") == "1":
        notify.send_if_changed(
            f"posting_metrics:{payload['week']}",
            text[:3900],
            min_interval_sec=86400 * 6,
        )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
