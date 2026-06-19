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


def _auth_ok(request: web.Request) -> bool:
    if not HA_NOTIFY_TOKEN:
        return False
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {HA_NOTIFY_TOKEN}"


async def _send_telegram_direct(message: str) -> tuple[bool, str]:
    if not TELEGRAM_TOKEN or not ADMIN_ID:
        return False, "telegram not configured"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(
                url, json={"chat_id": ADMIN_ID, "text": message}
            ) as resp:
                body = await resp.text()
                if resp.status == 200:
                    return True, "ok"
                return False, f"telegram HTTP {resp.status}: {body[:200]}"
    except Exception as exc:
        return False, str(exc)


async def _forward_vps(message: str, auth: str) -> tuple[bool, str]:
    if not FORWARD_URL:
        return False, "forward not configured"
    try:
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
            async with session.post(
                FORWARD_URL,
                json={"message": message},
                headers={"Authorization": auth, "Content-Type": "application/json"},
            ) as resp:
                body = await resp.text()
                if resp.status == 200:
                    return True, "forwarded"
                return False, f"forward HTTP {resp.status}: {body[:200]}"
    except Exception as exc:
        return False, str(exc)


async def _dispatch(message: str, auth: str) -> tuple[bool, str]:
    if FORWARD_ONLY and FORWARD_URL:
        ok, detail = await _forward_vps(message, auth)
    else:
        ok, detail = await _send_telegram_direct(message)
        if not ok and FORWARD_URL:
            log.warning("direct telegram failed: %s; forward to VPS", detail)
            ok, detail = await _forward_vps(message, auth)
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
    ok, detail = await _dispatch(message, request.headers.get("Authorization", ""))
    if not ok:
        log.error("notify failed: %s", detail)
        return web.json_response({"error": detail}, status=502)
    log.info("sent: %s (%s)", message[:80], detail)
    return web.json_response({"ok": True})


async def notify_get(request: web.Request) -> web.Response:
    """GET — для armbian, если POST по Tailscale не проходит."""
    if not _auth_ok(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    message = (request.query.get("message") or "").strip()
    if not message:
        return web.json_response({"error": "message required"}, status=400)
    ok, detail = await _dispatch(message, request.headers.get("Authorization", ""))
    if not ok:
        return web.json_response({"error": detail}, status=502)
    log.info("sent (GET): %s (%s)", message[:80], detail)
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
