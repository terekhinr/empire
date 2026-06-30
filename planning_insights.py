"""Сводка данных Empire для ИИ-брифинга (задачи, здоровье, пайплайн, метрики)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime
from typing import Any

from health_db import health_stats, health_summary
from metrics import weekly_events_summary
from planning_db import (
    SOURCE_AGENT,
    create_checklist,
    find_checklist_by_ref,
    get_connection,
    init_db,
    list_checklists,
    summary_counts,
)
from pii_validator import validate_payload_for_llm

WEIGHT_RE = re.compile(r"\[(\d+)%\]")
DAILY_FOCUS_REF_PREFIX = "empire-daily-focus-"


def _tasks_due_between(start: str, end: str, *, limit: int = 8) -> list[dict[str, Any]]:
    init_db()
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, title, due_date, priority
        FROM tasks
        WHERE status IN ('todo', 'doing')
          AND due_date IS NOT NULL
          AND due_date >= ? AND due_date <= ?
        ORDER BY due_date, priority DESC, id
        LIMIT ?
        """,
        (start, end, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _next_milestone() -> dict[str, Any] | None:
    init_db()
    conn = get_connection()
    today = date.today().isoformat()
    row = conn.execute(
        """
        SELECT id, title, due_date
        FROM tasks
        WHERE obsidian_source LIKE 'empire-audit:milestone:%'
          AND status IN ('todo', 'doing')
          AND due_date >= ?
        ORDER BY due_date, id
        LIMIT 1
        """,
        (today,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _workouts_last_days(days: int) -> int:
    return int(health_stats("week" if days <= 7 else "month").get("workouts_count") or 0)


def _llm_daily_focus(snapshot: dict[str, Any]) -> list[str] | None:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("EMPIRE_INSIGHTS_MODEL", "google/gemini-2.5-flash-preview").strip()
    payload = validate_payload_for_llm(
        {
            "today_tasks": snapshot.get("today_tasks", [])[:5],
            "overdue_count": snapshot.get("tasks", {}).get("overdue_count"),
            "next_milestone": snapshot.get("next_milestone"),
            "pipeline_pct": snapshot.get("pipeline", {}).get("percent_weighted"),
            "workouts_7d": snapshot.get("health", {}).get("workouts_last_7d"),
        }
    )
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Дай ровно 3 пункта фокуса на СЕГОДНЯ для владельца проекта Empire. "
                        "Каждый пункт — одна строка до 90 символов, без нумерации и маркеров."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "max_tokens": 280,
            "temperature": 0.25,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://neverretire.ru/tasks/",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        raw = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
        lines = [ln.strip(" •-\t0123456789.)") for ln in raw.splitlines() if ln.strip()]
        lines = [ln for ln in lines if len(ln) > 3][:3]
        return lines or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None


def _build_focus_items(snapshot: dict[str, Any], *, use_llm: bool) -> list[str]:
    if use_llm:
        llm_items = _llm_daily_focus(snapshot)
        if llm_items:
            return llm_items

    items: list[str] = []
    milestone = snapshot.get("next_milestone")
    if milestone:
        items.append(f"Веха {milestone.get('due_date')}: {milestone.get('title', '')[:70]}")

    for t in snapshot.get("today_tasks") or []:
        if len(items) >= 3:
            break
        items.append(f"Сегодня: {t['title'][:75]}")

    overdue = (snapshot.get("tasks") or {}).get("overdue_sample") or []
    if overdue and len(items) < 3:
        t = overdue[0]
        items.append(f"Просрочено: {t['title'][:70]}")

    w7 = int((snapshot.get("health") or {}).get("workouts_last_7d") or 0)
    if w7 == 0 and len(items) < 5:
        items.append("Силовая по программе — сохранить хотя бы 1 упражнение")

    pipe = snapshot.get("pipeline") or {}
    if pipe.get("percent_weighted") is not None and int(pipe["percent_weighted"]) < 20 and len(items) < 5:
        items.append("Пайплайн Empire: 1 пункт из чеклиста фазы 0")

    for c in snapshot.get("conclusions") or []:
        if len(items) >= 5:
            break
        if c not in items:
            items.append(c[:90])

    return items[:5] or ["Откройте чеклист Pipeline 2026 — отметьте 1 пункт"]


def _archive_old_daily_focus(keep_ref: str) -> None:
    init_db()
    conn = get_connection()
    conn.execute(
        """
        UPDATE checklists SET status='archived', updated_at=datetime('now')
        WHERE agent_ref LIKE ? AND agent_ref != ? AND status='active'
        """,
        (f"{DAILY_FOCUS_REF_PREFIX}%", keep_ref),
    )
    conn.commit()
    conn.close()


def ensure_daily_focus_checklist(items: list[str], *, day: str | None = None) -> int:
    day = day or date.today().isoformat()
    ref = f"{DAILY_FOCUS_REF_PREFIX}{day}"
    existing = find_checklist_by_ref(ref)
    if existing:
        return int(existing["id"])
    _archive_old_daily_focus(ref)
    return create_checklist(
        f"Фокус · {day}",
        description="Автобрифинг Empire (L2). Отметьте выполненное к вечеру.",
        source=SOURCE_AGENT,
        agent_ref=ref,
        tags=["empire", "daily", "focus", "agent"],
        items=items[:5],
    )


def format_daily_telegram(data: dict[str, Any]) -> str:
    day = data.get("day") or date.today().isoformat()
    lines = [f"<b>Empire · фокус дня</b>", f"{day} · 08:00 MSK", ""]
    for i, item in enumerate(data.get("focus_items") or [], 1):
        lines.append(f"{i}. {item}")
    tasks = data.get("tasks") or {}
    pipe = data.get("pipeline") or {}
    lines.append("")
    lines.append(
        f"Просрочено: {tasks.get('overdue_count', 0)} · "
        f"Сегодня: {len(data.get('today_tasks') or [])} · "
        f"Пайплайн: {pipe.get('percent_weighted', '—')}%"
    )
    lines.append('<a href="https://neverretire.ru/tasks/">Открыть Empire Tasks</a>')
    return "\n".join(lines)


def send_daily_telegram(text: str) -> bool:
    token = (os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
    admin = (os.getenv("ADMIN_ID") or os.getenv("EMPIRE_ADMIN_ID") or "0").strip()
    if not token or not admin or admin == "0":
        return False
    body = json.dumps(
        {"chat_id": int(admin), "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def load_daily_briefing(*, day: str | None = None) -> dict[str, Any] | None:
    from pathlib import Path

    day = day or date.today().isoformat()
    path = Path(__file__).resolve().parent / "data" / "insights" / f"daily_{day}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_daily_briefing(*, use_llm: bool = True) -> dict[str, Any]:
    """Утренний снимок L1: данные + выводы + фокус дня."""
    today = date.today().isoformat()
    base = build_empire_insights(use_llm=use_llm)
    today_tasks = _tasks_due_between(today, today, limit=6)
    week_end = (date.today()).isoformat()  # extend: +7 days
    from datetime import timedelta

    week_end_date = (date.today() + timedelta(days=7)).isoformat()
    week_tasks = _tasks_due_between(today, week_end_date, limit=20)
    milestone = _next_milestone()

    snapshot: dict[str, Any] = {
        **base,
        "kind": "daily",
        "day": today,
        "today_tasks": [{"title": t["title"], "due_date": t["due_date"]} for t in today_tasks],
        "week_task_count": len(week_tasks),
        "next_milestone": milestone,
        "health": {
            **(base.get("health") or {}),
            "workouts_last_7d": _workouts_last_days(7),
        },
    }
    snapshot["focus_items"] = _build_focus_items(snapshot, use_llm=use_llm)
    snapshot["telegram_preview"] = format_daily_telegram(snapshot)
    return snapshot


def save_daily_briefing_file(data: dict[str, Any] | None = None, *, use_llm: bool = True) -> str:
    from pathlib import Path

    data = data or build_daily_briefing(use_llm=use_llm)
    out_dir = Path(__file__).resolve().parent / "data" / "insights"
    out_dir.mkdir(parents=True, exist_ok=True)
    day = data.get("day") or date.today().isoformat()
    path = out_dir / f"daily_{day}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def run_daily_briefing(*, use_llm: bool = True, notify_telegram: bool = True) -> dict[str, Any]:
    """L1+L2: файл, чеклист фокуса, Telegram."""
    use_llm = use_llm and bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    data = build_daily_briefing(use_llm=use_llm)
    path = save_daily_briefing_file(data)
    cid = ensure_daily_focus_checklist(data.get("focus_items") or [])
    data["file_path"] = path
    data["checklist_id"] = cid
    data["telegram_sent"] = False
    if notify_telegram:
        data["telegram_sent"] = send_daily_telegram(data.get("telegram_preview") or "")
    return data


def _overdue_tasks(limit: int = 12) -> list[dict[str, Any]]:
    init_db()
    conn = get_connection()
    today = date.today().isoformat()
    rows = conn.execute(
        """
        SELECT id, title, due_date, priority
        FROM tasks
        WHERE status IN ('todo', 'doing')
          AND due_date IS NOT NULL
          AND due_date < ?
        ORDER BY due_date, priority DESC
        LIMIT ?
        """,
        (today, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _pipeline_progress() -> dict[str, Any] | None:
    for cl in list_checklists(status="active", limit=50):
        if cl.get("agent_ref") == "empire-pipeline-2026":
            total = int(cl.get("items_total") or 0)
            done = int(cl.get("items_done") or 0)
            pct = round(100 * done / total) if total else 0
            weighted = _weighted_pipeline_pct(int(cl["id"]))
            return {
                "title": cl.get("title"),
                "items_done": done,
                "items_total": total,
                "percent_simple": pct,
                "percent_weighted": weighted,
            }
    return None


def _weighted_pipeline_pct(checklist_id: int) -> int:
    init_db()
    conn = get_connection()
    rows = conn.execute(
        "SELECT title, status FROM checklist_items WHERE checklist_id = ?",
        (checklist_id,),
    ).fetchall()
    conn.close()
    total_w = done_w = 0
    for row in rows:
        m = WEIGHT_RE.match(row["title"] or "")
        w = int(m.group(1)) if m else 1
        total_w += w
        if row["status"] == "done":
            done_w += w
    return round(100 * done_w / total_w) if total_w else 0


def _rule_conclusions(snapshot: dict[str, Any]) -> list[str]:
    out: list[str] = []
    tasks = snapshot.get("tasks") or {}
    health = snapshot.get("health") or {}
    pipe = snapshot.get("pipeline") or {}
    overdue = int(tasks.get("overdue_count") or 0)

    if overdue >= 8:
        out.append(f"Просрочено {overdue} задач — перенесите даты или закройте неактуальные.")
    elif overdue >= 1:
        out.append(f"Просрочено {overdue} задач — начните с самой приоритетной.")

    w_pct = pipe.get("percent_weighted")
    if w_pct is not None and w_pct < 15:
        out.append(
            f"Пайплайн Empire {w_pct}% по весам — фокус на ближайшую веху (см. чеклист Pipeline 2026)."
        )
    elif w_pct is not None and w_pct >= 40:
        out.append(f"Пайплайн Empire {w_pct}% — хороший темп, держите ритм фазы.")

    wc = int(health.get("workouts_last_31d") or 0)
    if wc == 0:
        out.append("За месяц нет силовых — откройте «Программа» и сохраните хотя бы одну тренировку.")
    elif wc < 4:
        out.append(f"Силовых за месяц: {wc} — до 3×/нед по программе есть запас.")

    delta = health.get("weight_change_kg")
    if isinstance(delta, (int, float)) and delta > 0.8:
        out.append(f"Вес +{delta:.1f} кг к прошлому замеру — проверьте калории и шаги.")
    elif isinstance(delta, (int, float)) and delta < -0.8:
        out.append(f"Вес {delta:.1f} кг — убедитесь, что дефицит/набор осознанный.")

    todo = int(tasks.get("tasks_todo") or 0)
    doing = int(tasks.get("tasks_doing") or 0)
    if doing > 5:
        out.append(f"В работе {doing} задач — завершите 1–2, чтобы не распыляться.")

    events = snapshot.get("empire_events_7d") or {}
    if events and sum(events.values()) < 5:
        out.append("Мало событий в analytics за неделю — проверьте автопост и Metrika.")

    if not out:
        out.append("Критичных отклонений нет. Следующий шаг — ближайшая веха в календаре.")
    return out


def _llm_narrative(snapshot: dict[str, Any]) -> str | None:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("EMPIRE_INSIGHTS_MODEL", "google/gemini-2.5-flash-preview").strip()
    payload = validate_payload_for_llm(
        {
            "tasks_todo": snapshot.get("tasks", {}).get("tasks_todo"),
            "overdue": snapshot.get("tasks", {}).get("overdue_count"),
            "pipeline_weighted_pct": snapshot.get("pipeline", {}).get("percent_weighted"),
            "workouts_31d": snapshot.get("health", {}).get("workouts_last_31d"),
            "weight_kg": snapshot.get("health", {}).get("latest_weight_kg"),
            "conclusions_draft": snapshot.get("conclusions"),
        }
    )
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты личный аналитик проекта Empire. По цифрам дай 3–5 коротких выводов "
                        "на русском: что сделать на этой неделе. Без воды, без PII, без выдуманных цифр."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            "max_tokens": 500,
            "temperature": 0.3,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://neverretire.ru/tasks/",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip() or None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return None


def build_empire_insights(*, use_llm: bool = True) -> dict[str, Any]:
    """Агрегат для PWA и weekly cron."""
    counts = summary_counts()
    overdue = _overdue_tasks()
    h_sum = health_summary()
    h_stats = health_stats("month")
    latest = h_sum.get("summary") or {}
    pipe = _pipeline_progress()

    snapshot: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "tasks": {
            **counts,
            "overdue_count": len(overdue),
            "overdue_sample": [
                {"title": t["title"], "due_date": t["due_date"]} for t in overdue[:5]
            ],
        },
        "health": {
            "latest_weight_kg": latest.get("weight_kg"),
            "weight_change_kg": latest.get("weight_change_kg"),
            "measurements_count": h_sum.get("measurements_count"),
            "workouts_total": h_sum.get("workouts_count"),
            "workouts_last_31d": h_stats.get("workouts_count"),
        },
        "pipeline": pipe,
        "checklists_active": len(list_checklists(status="active")),
        "empire_events_7d": weekly_events_summary(7),
    }
    snapshot["conclusions"] = _rule_conclusions(snapshot)
    if use_llm:
        narrative = _llm_narrative(snapshot)
        if narrative:
            snapshot["narrative"] = narrative
    snapshot["llm_used"] = bool(snapshot.get("narrative"))
    return snapshot


def save_empire_insights_file(*, use_llm: bool = True) -> str:
    from pathlib import Path

    out_dir = Path(__file__).resolve().parent / "data" / "insights"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"empire_insights_{date.today().isoformat()}.json"
    data = build_empire_insights(use_llm=use_llm)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)
