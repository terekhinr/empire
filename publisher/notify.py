"""Ops-уведомления автопост-бота в Telegram (admin chat)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger("empire.publisher")
MSK = ZoneInfo("Europe/Moscow")

DEFAULT_BOT_SETTINGS: dict[str, Any] = {
    "admin_chat_id": "",
    "notify_on": ["published", "skipped", "failed"],
    "digest": "daily",
    "last_digest_at": None,
    "min_body_chars": 80,
    "require_image": True,
    "dedupe_days": 30,
    "dedupe_threshold": 0.90,
}


def normalize_bot_settings(raw: dict | None) -> dict[str, Any]:
    out = dict(DEFAULT_BOT_SETTINGS)
    if isinstance(raw, dict):
        out.update({k: raw[k] for k in raw if k in out or k == "last_digest_at"})
        if "notify_on" in raw and isinstance(raw["notify_on"], list):
            out["notify_on"] = [str(x) for x in raw["notify_on"]]
    return out


def resolve_admin_chat_id(settings: dict[str, Any]) -> str:
    cid = str(settings.get("admin_chat_id") or "").strip()
    if cid:
        return cid
    env = (os.getenv("ADMIN_ID") or "").strip()
    return env


def telegram_token() -> str:
    return (os.getenv("TELEGRAM_TOKEN") or "").strip()


def send_admin_text(chat_id: str, text: str, *, token: str | None = None) -> tuple[bool, str]:
    tok = (token or telegram_token()).strip()
    if not tok:
        return False, "no_telegram_token"
    if not chat_id:
        return False, "no_admin_chat"
    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    try:
        r = requests.post(
            url,
            data={"chat_id": chat_id, "text": text[:3900], "disable_web_page_preview": "true"},
            timeout=30,
        )
        if r.status_code >= 400:
            return False, f"tg_http_{r.status_code}"
        return True, "sent"
    except Exception as exc:
        logger.warning("publisher notify failed: %s", type(exc).__name__)
        return False, str(exc)[:120]


def format_event(rec: dict[str, Any]) -> str:
    pid = rec.get("project_id") or "?"
    title = (rec.get("title") or "")[:60]
    sched = (rec.get("scheduled_at") or "")[-5:] or "--:--"
    status = rec.get("status") or ("published" if rec.get("ok") else "failed")
    detail = (rec.get("detail") or "")[:120]
    img = rec.get("image_source") or ""
    if status == "skipped" or rec.get("skipped"):
        if str(detail).startswith("duplicate"):
            return f"Dup skip {pid} {sched}: {detail} «{title}»"
        return f"Skip {pid} {sched}: {detail or 'skipped'} «{title}»"
    if rec.get("ok") and status in ("published", "test_sent"):
        mark = "✓" if status == "published" else "○"
        stub = " [stub]" if img == "stub" else ""
        return f"{mark} {pid} {sched} «{title}»{stub}"
    return f"Fail {pid} {sched}: {detail} «{title}»"


def event_kind(rec: dict[str, Any]) -> str:
    if rec.get("skipped") or rec.get("status") == "skipped":
        return "skipped"
    if rec.get("ok"):
        return "published"
    return "failed"


def notify_tick_results(
    settings: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    mode: str,
) -> list[dict[str, Any]]:
    """Отправить алерты по результатам tick. В test — тоже (чтобы видеть ops)."""
    settings = normalize_bot_settings(settings)
    notify_on = set(settings.get("notify_on") or [])
    chat = resolve_admin_chat_id(settings)
    out: list[dict[str, Any]] = []
    if not results:
        return out
    lines: list[str] = []
    for rec in results:
        kind = event_kind(rec)
        # test_sent считаем как published для notify_on
        key = "published" if kind == "published" else kind
        if key not in notify_on and kind not in notify_on:
            continue
        lines.append(format_event({**rec, "status": kind if kind != "published" else (
            "test_sent" if mode == "test" else "published"
        )}))
    if not lines:
        return out
    prefix = "[studio test]\n" if mode == "test" else "[studio]\n"
    ok, detail = send_admin_text(chat, prefix + "\n".join(lines))
    out.append({"ok": ok, "detail": detail, "lines": len(lines)})
    return out


def build_digest(data: dict[str, Any]) -> str:
    from publisher.bank import bank_days_remaining

    outbox = data.get("outbox") or []
    cutoff = datetime.now(MSK) - timedelta(days=1)
    pub = skip = fail = 0
    for rec in outbox:
        at = rec.get("at") or ""
        try:
            dt = datetime.fromisoformat(at.replace("Z", "+00:00")).astimezone(MSK)
        except ValueError:
            continue
        if dt < cutoff:
            continue
        kind = event_kind(rec)
        if kind == "published":
            pub += 1
        elif kind == "skipped":
            skip += 1
        else:
            fail += 1
    days = bank_days_remaining(data)
    return (
        f"[studio digest]\n"
        f"24ч: published {pub} / skip {skip} / fail {fail}\n"
        f"запас банка ~{days} дн."
    )


def maybe_send_digest(data: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any] | None:
    settings = normalize_bot_settings(data.get("bot_settings"))
    freq = (settings.get("digest") or "off").strip().lower()
    if freq not in ("daily", "weekly"):
        return None
    now = now or datetime.now(MSK)
    last_raw = settings.get("last_digest_at")
    last: datetime | None = None
    if last_raw:
        try:
            last = datetime.fromisoformat(str(last_raw).replace("Z", "+00:00")).astimezone(MSK)
        except ValueError:
            last = None
    need = False
    if last is None:
        need = True
    elif freq == "daily" and (now - last) >= timedelta(hours=20):
        need = True
    elif freq == "weekly" and (now - last) >= timedelta(days=6):
        need = True
    if not need:
        return None
    chat = resolve_admin_chat_id(settings)
    text = build_digest(data)
    ok, detail = send_admin_text(chat, text)
    settings["last_digest_at"] = now.isoformat()
    data["bot_settings"] = settings
    return {"ok": ok, "detail": detail, "text": text}
