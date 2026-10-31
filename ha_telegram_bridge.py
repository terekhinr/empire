#!/usr/bin/env python3
"""Мост HA → Telegram. Локально или пересылка на VPS, если api.telegram.org недоступен."""
from __future__ import annotations

import logging
import os

import aiohttp
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ha_telegram_bridge")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")
HA_NOTIFY_TOKEN = os.getenv("HA_NOTIFY_TOKEN", "")
BIND = os.getenv("HA_NOTIFY_BIND", "0.0.0.0")
PORT = int(os.getenv("HA_NOTIFY_PORT", "8766"))
# Если с armbian не открывается api.telegram.org — пересылка на мост VPS (Tailscale):
FORWARD_URL = os.getenv("HA_NOTIFY_FORWARD_URL", "").strip()
FORWARD_ONLY = os.getenv("HA_NOTIFY_FORWARD_ONLY", "").lower() in ("1", "true", "yes")
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=12)

# Сообщения с камер (Ezviz motion) в Telegram не нужны.
_CAMERA_NOTIFY_MARKERS = (
    "камера",
    "ezviz",
    "motion alarm",
    "движение (прихожая)",
    "движение (подъезд)",
    "движение (улица)",
    "движение в отпуске",
)


def _is_camera_notify(message: str) -> bool:
    low = message.casefold()
    return any(m in low for m in _CAMERA_NOTIFY_MARKERS)


def _auth_ok(request: web.Request) -> bool:
    if not HA_NOTIFY_TOKEN:
        return False
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {HA_NOTIFY_TOKEN}"


def _domofon_keyboard() -> dict:
    """Inline-кнопки для звонка в домофон (callback ловит empire_main)."""
    return {
        "inline_keyboard": [
            [
                {"text": "🚪 Открыть", "callback_data": "domofon_open"},
                {"text": "📦 Курьер", "callback_data": "domofon_delivery"},
            ],
            [
                {"text": "📵 Сброс", "callback_data": "domofon_reject"},
            ],
        ]
    }


def _reply_markup_for(message: str, body: dict | None = None) -> dict | None:
    if body and isinstance(body.get("reply_markup"), dict):
        return body["reply_markup"]
    if body and body.get("domofon_buttons"):
        return _domofon_keyboard()
    low = message.casefold()
    if "звонок в домофон" in low or low.strip().startswith("домофон"):
        return _domofon_keyboard()
    return None


async def _send_telegram_direct(
    message: str, reply_markup: dict | None = None
) -> tuple[bool, str]:
    if not TELEGRAM_TOKEN or not ADMIN_ID:
        return False, "telegram not configured"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload: dict = {"chat_id": ADMIN_ID, "text": message}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                body = await resp.text()
                if resp.status != 200:
                    return False, f"telegram HTTP {resp.status}: {body[:200]}"
                import json as _json

                try:
                    data = _json.loads(body)
                except Exception:
                    data = {}
                result = (data or {}).get("result") or {}
                if reply_markup and not result.get("reply_markup"):
                    log.error(
                        "telegram accepted message but stripped reply_markup: %s",
                        body[:300],
                    )
                    return False, "telegram stripped reply_markup"
                return True, "ok"
    except Exception as exc:
        return False, str(exc)


async def _forward_vps(
    message: str, auth: str, reply_markup: dict | None = None
) -> tuple[bool, str]:
    if not FORWARD_URL:
        return False, "forward not configured"
    payload: dict = {"message": message}
    if reply_markup:
        payload["reply_markup"] = reply_markup
        payload["domofon_buttons"] = True
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(
                FORWARD_URL,
                json=payload,
                headers={"Authorization": auth, "Content-Type": "application/json"},
            ) as resp:
                body = await resp.text()
                if resp.status == 200:
                    return True, "forwarded"
                return False, f"forward HTTP {resp.status}: {body[:200]}"
    except Exception as exc:
        return False, str(exc)


async def _dispatch(
    message: str, auth: str, reply_markup: dict | None = None
) -> tuple[bool, str]:
    if FORWARD_ONLY and FORWARD_URL:
        ok, detail = await _forward_vps(message, auth, reply_markup)
    else:
        ok, detail = await _send_telegram_direct(message, reply_markup)
        if not ok and FORWARD_URL:
            log.warning("direct telegram failed: %s; forward to VPS", detail)
            ok, detail = await _forward_vps(message, auth, reply_markup)
    return ok, detail


async def notify(request: web.Request) -> web.Response:
    if not _auth_ok(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)
    message = (body.get("message") or "").strip()
    if not message:
        return web.json_response({"error": "message required"}, status=400)
    if _is_camera_notify(message):
        log.info("dropped camera notify: %s", message[:80])
        return web.json_response({"ok": True, "dropped": "camera"})
    markup = _reply_markup_for(message, body)
    ok, detail = await _dispatch(
        message, request.headers.get("Authorization", ""), markup
    )
    if not ok:
        log.error("notify failed: %s", detail)
        return web.json_response({"error": detail}, status=502)
    log.info("sent: %s (%s) kb=%s", message[:80], detail, bool(markup))
    return web.json_response({"ok": True})


async def notify_get(request: web.Request) -> web.Response:
    """GET — для armbian, если POST по Tailscale не проходит."""
    if not _auth_ok(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    message = (request.query.get("message") or "").strip()
    if not message:
        return web.json_response({"error": "message required"}, status=400)
    if _is_camera_notify(message):
        log.info("dropped camera notify (GET): %s", message[:80])
        return web.json_response({"ok": True, "dropped": "camera"})
    markup = _reply_markup_for(message, {"domofon_buttons": request.query.get("domofon") == "1"})
    ok, detail = await _dispatch(
        message, request.headers.get("Authorization", ""), markup
    )
    if not ok:
        return web.json_response({"error": detail}, status=502)
    log.info("sent (GET): %s (%s) kb=%s", message[:80], detail, bool(markup))
    return web.json_response({"ok": True})


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "ha_telegram_bridge"})


def main() -> None:
    app = web.Application()
    app.router.add_post("/notify", notify)
    app.router.add_get("/notify", notify_get)
    app.router.add_get("/health", health)
    log.info(
        "listening on %s:%s forward=%s only=%s",
        BIND,
        PORT,
        FORWARD_URL or "off",
        FORWARD_ONLY,
    )
    web.run_app(app, host=BIND, port=PORT)


if __name__ == "__main__":
    main()
