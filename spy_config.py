"""Разведка контента (ТЗ май 2026): только Gdepar + Stern, только живой Telethon."""

from __future__ import annotations

import os
from pathlib import Path

# Персоны, для которых вообще предусмотрена TG-разведка конкурентов
SPY_CONTENT_PERSONAS = frozenset({"gdepar", "stern"})

# Сад / Ленин / Пенсия — не spy (пенсия: RSS + вкладка «Пенсия · новости»)
SPY_EXCLUDED_PERSONAS = frozenset({"garden", "lenin", "pension"})


def telethon_session_path() -> Path:
    root = Path(__file__).resolve().parent
    return Path(os.getenv("TELETHON_SESSION", str(root / "empire_spy")))


def telethon_configured() -> bool:
    return bool(os.getenv("TELETHON_API_ID", "").strip()) and bool(
        os.getenv("TELETHON_API_HASH", "").strip()
    )


def telethon_session_ready() -> bool:
    p = telethon_session_path()
    if p.suffix == ".session" and p.is_file():
        return True
    return p.with_suffix(".session").is_file()


def spy_live_enabled() -> bool:
    """Реальная разведка по каналам из spy_competitors.json."""
    return telethon_configured() and telethon_session_ready()


def spy_dry_run_allowed() -> bool:
    """RSS-заглушки с фейковым ER — только явно SPY_ALLOW_DRY_RUN=1 (отладка)."""
    return os.getenv("SPY_ALLOW_DRY_RUN", "").strip().lower() in ("1", "true", "yes")


def persona_uses_spy_content(persona: str) -> bool:
    return (persona or "").strip() in SPY_CONTENT_PERSONAS


def can_run_spy_pipeline() -> bool:
    return spy_live_enabled() or spy_dry_run_allowed()


def can_create_spy_draft(persona: str) -> tuple[bool, str]:
    if not persona_uses_spy_content(persona):
        return False, "spy_not_for_persona"
    if not spy_live_enabled() and not spy_dry_run_allowed():
        return False, "spy_telethon_required"
    return True, ""
