#!/usr/bin/env python3
"""Автопост только curated-слотов: Garden/Lenin без LLM-автопубликации."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "auto_publish.json"


def main() -> int:
    cfg = json.loads(PATH.read_text(encoding="utf-8"))
    rubrics = cfg.setdefault("rubrics", {})

    # Garden: LLM-слоты (06:30/12:00/16:00) — только ручной approve; автопост lunar+promo.
    cfg["personas"]["garden"] = {
        "enabled": False,
        "min_body_chars": 350,
        "require_zero_regen": False,
        "max_selfcrit_issues": 3,
    }
    rubrics["garden_lunar"] = {
        "enabled": True,
        "personas": ["garden"],
        "topic_markers": ["[Лунный календарь]", "[SPECIAL:kizima_lunar]"],
        "min_body_chars": 180,
        "skip_body_floor": True,
        "require_image": False,
        "require_zero_regen": True,
        "require_zero_badimg": True,
        "max_selfcrit_issues": 99,
    }
    rubrics["garden_bot_promo"] = {
        "enabled": True,
        "personas": ["garden"],
        "topic_markers": ["[SPECIAL:bot_promo]"],
        "min_body_chars": 120,
        "skip_body_floor": True,
        "require_image": False,
        "require_zero_regen": True,
        "require_zero_badimg": True,
        "max_selfcrit_issues": 99,
    }

    # Lenin: рубрики + ПСС + сказка + календарь + донат — curated; марксизм/свободная тема — вручную.
    cfg["personas"]["lenin"] = {
        "enabled": False,
        "min_body_chars": 350,
        "require_zero_regen": False,
        "max_selfcrit_issues": 3,
    }
    rubrics["lenin_calendar"] = {
        "enabled": True,
        "personas": ["lenin"],
        "topic_markers": ["[#Вэтотдень]", "[В этот день]"],
        "min_body_chars": 120,
        "skip_body_floor": True,
        "require_image": True,
        "require_zero_regen": True,
        "require_zero_badimg": True,
        "max_selfcrit_issues": 99,
    }
    rubrics["lenin_pss"] = {
        "enabled": True,
        "personas": ["lenin"],
        "topic_markers": ["[ПСС · фрагмент]"],
        "min_body_chars": 200,
        "skip_body_floor": True,
        "require_image": True,
        "require_zero_regen": True,
        "require_zero_badimg": True,
        "max_selfcrit_issues": 99,
    }
    rubrics["lenin_book"] = {
        "enabled": True,
        "personas": ["lenin"],
        "topic_markers": ["[Сказка на ночь]"],
        "min_body_chars": 200,
        "skip_body_floor": True,
        "require_image": False,
        "require_zero_regen": True,
        "require_zero_badimg": True,
        "max_selfcrit_issues": 99,
    }
    rubrics["lenin_channel_support"] = {
        "enabled": True,
        "personas": ["lenin"],
        "topic_markers": ["[SPECIAL:channel_support]"],
        "min_body_chars": 80,
        "skip_body_floor": True,
        "require_image": False,
        "require_zero_regen": True,
        "require_zero_badimg": True,
        "max_selfcrit_issues": 99,
    }
    if "lenin_curated" in rubrics:
        rubrics["lenin_curated"]["enabled"] = True

    PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK auto_publish — garden/lenin: curated-only autopublish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
