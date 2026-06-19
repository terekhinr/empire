"""Deep links на донат-бота — только канал Ленин."""

from __future__ import annotations

import os
import re

DONATE_CAMPAIGN = "lenin"
_CAMPAIGN_RE = re.compile(r"^donate_([a-z0-9_]+)$", re.I)

# Подсказки, если пользователь перешёл с чужой метки (старые ссылки)
_ALIEN_CAMPAIGN_HINT = {
    "gdepar": "Канал «Где пар» — карта бань на https://gdepar.ru (промо в постах канала).",
    "garden": "«Сад и огород» — гайды в боте продаж (ссылка в закрепе канала, не донат).",
    "stern": "«Железная спина» — отдельный бот курса (tripwire / офисный размин).",
    "empire": "Этот бот принимает донаты только для канала «Ленин».",
}


def bot_username() -> str | None:
    u = os.getenv("EMPIRE_DONATE_BOT_USERNAME", "").strip().lstrip("@")
    return u or None


def donate_deep_link(campaign: str = DONATE_CAMPAIGN, source_id: str | None = None) -> str | None:
    """Ссылка только для campaign=lenin."""
    if campaign != DONATE_CAMPAIGN:
        return None
    user = bot_username()
    if not user:
        return None
    start = f"donate_{DONATE_CAMPAIGN}"
    if source_id:
        safe = re.sub(r"[^a-zA-Z0-9_]", "", source_id)[:32]
        if safe:
            start = f"{start}_{safe}"
    return f"https://t.me/{user}?start={start}"


def parse_start_param(param: str | None) -> tuple[str, str | None]:
    """Возвращает (campaign, source). Для оплаты допустим только lenin."""
    if not param:
        return DONATE_CAMPAIGN, None
    m = _CAMPAIGN_RE.match(param.strip())
    if not m:
        return DONATE_CAMPAIGN, None
    rest = m.group(1)
    if rest == DONATE_CAMPAIGN:
        return DONATE_CAMPAIGN, None
    if rest.startswith(f"{DONATE_CAMPAIGN}_"):
        src = rest[len(DONATE_CAMPAIGN) + 1 :]
        return DONATE_CAMPAIGN, src or None
    if "_" in rest:
        camp, src = rest.split("_", 1)
        return camp.lower(), src or None
    return rest.lower(), None


def alien_campaign_message(campaign: str) -> str | None:
    """Текст, если пришли не с donate_lenin."""
    if campaign == DONATE_CAMPAIGN:
        return None
    hint = _ALIEN_CAMPAIGN_HINT.get(campaign)
    if hint:
        return hint + "\n\nЗдесь можно поддержать только канал «Ленин» — выберите сумму ниже."
    return (
        "Этот бот — только для донатов канала «Ленин».\n"
        "Для других проектов см. закреп соответствующего канала."
    )
