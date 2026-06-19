"""Каналы публикации по персоне (data/publish_channels.json)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

_CFG_PATH = Path(__file__).resolve().parent / "data" / "publish_channels.json"


@lru_cache(maxsize=1)
def _load_cfg() -> dict:
    try:
        with open(_CFG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"use_profile": "tg_only", "profiles": {"tg_only": {}}}


def _profile_for_persona(persona_key: str) -> str:
    cfg = _load_cfg()
    overrides = cfg.get("persona_profile") or {}
    pk = (persona_key or "").strip()
    if pk in overrides:
        return str(overrides[pk])
    return str(cfg.get("use_profile", "tg_only"))


def channels_for_persona(persona_key: str) -> list[str]:
    """Список каналов для approve/publish (tg, vk_wall, dzen_rss, …)."""
    cfg = _load_cfg()
    profile = _profile_for_persona(persona_key)
    channels = list(
        (cfg.get("profiles") or {}).get(profile, {}).get(persona_key, ["tg"])
    )
    if not channels:
        channels = ["tg"]
    if not os.getenv("VK_ACCESS_TOKEN", "").strip():
        channels = [c for c in channels if c != "vk_wall"]
    return channels


def reload_publish_channels_config() -> None:
    _load_cfg.cache_clear()
