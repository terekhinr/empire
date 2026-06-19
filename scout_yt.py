"""YouTube Shorts trends — каркас (ТЗ §4.5, без ключа = заглушка)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("empire.scout_yt")
OUT_PATH = Path(__file__).resolve().parent / "data" / "yt_trends.json"


def fetch_yt_trends_stub(*, persona: str = "stern", niche: str = "fitness shorts") -> dict:
    """Без YOUTUBE_API_KEY пишет placeholder; с ключом — расширить позже."""
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "persona": persona,
        "niche": niche,
        "mode": "api" if key else "stub",
        "items": [
            {"title": "3 ошибки в становой с гирей", "views_proxy": 120000},
            {"title": "Разминка 5 минут перед работой", "views_proxy": 89000},
        ],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
