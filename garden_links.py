"""Ссылки на бот продаж «Сад и огород»."""

from __future__ import annotations

import os
import re


def bot_username() -> str | None:
    u = os.getenv("EMPIRE_GARDEN_BOT_USERNAME", "").strip().lstrip("@")
    return u or None


def garden_bot_link(source_id: str | None = None) -> str | None:
    user = bot_username()
    if not user:
        return None
    start = "channel"
    if source_id:
        safe = re.sub(r"[^a-zA-Z0-9_]", "", source_id)[:32]
        if safe:
            start = safe
    return f"https://t.me/{user}?start={start}"
