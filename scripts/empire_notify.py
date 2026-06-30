#!/usr/bin/env python3
"""Единая отправка уведомлений Empire → Telegram (ADMIN_ID)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = Path(os.getenv("EMPIRE_DIAG_STATE", "/var/log/empire/diagnostics-state.json"))


def _load_state() -> dict:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def send(
    text: str,
    *,
    parse_mode: str | None = None,
    disable_preview: bool = True,
    retries: int = 3,
) -> bool:
    load_dotenv(ROOT / ".env")
    token = (os.getenv("TELEGRAM_TOKEN") or "").strip()
    admin = (os.getenv("ADMIN_ID") or "").strip()
    if not token or not admin:
        return False
    payload: dict = {
        "chat_id": int(admin),
        "text": text,
        "disable_web_page_preview": disable_preview,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for attempt in range(max(1, retries)):
        try:
            r = httpx.post(url, json=payload, timeout=45.0)
            if r.status_code == 200:
                st = _load_state()
                st["last_telegram_ok"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                save_state(st)
                return True
            if r.status_code == 429:
                time.sleep(2 + attempt * 2)
                continue
        except Exception:
            time.sleep(1 + attempt)
    return False


def _tg_creds() -> tuple[str, str] | None:
    load_dotenv(ROOT / ".env")
    token = (os.getenv("TELEGRAM_TOKEN") or "").strip()
    admin = (os.getenv("ADMIN_ID") or "").strip()
    if not token or not admin:
        return None
    return token, admin


def send_file(
    path: Path,
    *,
    caption: str = "",
    as_audio: bool = True,
    retries: int = 3,
) -> bool:
    """Send file to ADMIN_ID. Telegram bot limit: 50 MB per file."""
    creds = _tg_creds()
    if not creds or not path.is_file():
        return False
    token, admin = creds
    method = "sendAudio" if as_audio else "sendDocument"
    url = f"https://api.telegram.org/bot{token}/{method}"
    field = "audio" if as_audio else "document"
    for attempt in range(max(1, retries)):
        try:
            with path.open("rb") as f:
                data: dict = {"chat_id": int(admin)}
                if caption:
                    data["caption"] = caption[:1024]
                if as_audio:
                    data["title"] = path.stem[:64]
                r = httpx.post(
                    url,
                    data=data,
                    files={field: (path.name, f, "audio/mpeg")},
                    timeout=600.0,
                )
            if r.status_code == 200:
                return True
            if r.status_code == 429:
                time.sleep(3 + attempt * 3)
                continue
            print(f"telegram {method} failed: {r.status_code} {r.text[:200]}", flush=True)
        except Exception as exc:
            print(f"telegram {method} error: {exc}", flush=True)
            time.sleep(2 + attempt)
    return False


def send_if_changed(key: str, text: str, *, min_interval_sec: int = 3600) -> bool:
    """Не спамить: шлём только если текст изменился или прошёл min_interval."""
    st = _load_state()
    alerts = st.setdefault("alerts", {})
    prev = alerts.get(key) or {}
    now = time.time()
    if prev.get("text") == text and (now - prev.get("ts", 0)) < min_interval_sec:
        return False
    ok = send(text)
    if ok:
        alerts[key] = {"text": text, "ts": now}
        save_state(st)
    return ok
