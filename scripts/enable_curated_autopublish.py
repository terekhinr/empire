#!/usr/bin/env python3
"""Включить автопост курированных каналов (gdepar duo/classic, stern matrix)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "auto_publish.json"


def main() -> int:
    cfg = json.loads(PATH.read_text(encoding="utf-8"))
    cfg["_readme"] = (
        "Июль 2026: автопост по расписанию для garden/lenin/gdepar/stern. "
        "Курированные дуэт/Stern matrix — с готовым image_file."
    )
    cfg["enabled"] = True
    cfg["scheduled_only"] = True

    cfg["personas"]["gdepar"] = {
        "enabled": True,
        "min_body_chars": 260,
        "skip_body_floor": True,
        "max_selfcrit_issues": 99,
        "require_zero_regen": True,
        "require_zero_badimg": True,
    }
    cfg["personas"]["stern"] = {
        "enabled": True,
        "min_body_chars": 240,
        "skip_body_floor": True,
        "max_selfcrit_issues": 5,
        "require_zero_regen": False,
        "require_zero_badimg": True,
    }

    cfg["rubrics"]["gdepar_duo_curated"]["enabled"] = True
    cfg["rubrics"]["gdepar_classic_banya"]["enabled"] = True
    cfg["rubrics"]["stern_curated"]["enabled"] = True
    cfg["rubrics"]["gdepar_promo_map"] = {
        "enabled": True,
        "personas": ["gdepar"],
        "topic_markers": ["[SPECIAL:promo_map]"],
        "min_body_chars": 120,
        "skip_body_floor": True,
        "require_image": False,
        "require_zero_regen": True,
        "require_zero_badimg": True,
        "max_selfcrit_issues": 99,
    }
    markers = cfg["rubrics"]["stern_curated"].setdefault("topic_markers", [])
    if "[Историческое наследие]" not in markers:
        markers.append("[Историческое наследие]")

    cfg["rubrics"]["stern_matrix_curated"] = {
        "enabled": True,
        "personas": ["stern"],
        "topic_markers": [
            "[Рутина]",
            "[Психология]",
            "[Восстановление]",
            "[Питание]",
            "[Срывы]",
            "[Мотивация]",
            "[Возрастной тренинг]",
            "[Ответы]",
        ],
        "min_body_chars": 220,
        "skip_body_floor": True,
        "require_image": True,
        "require_zero_regen": True,
        "require_zero_badimg": True,
        "max_selfcrit_issues": 99,
    }

    PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK auto_publish.json — gdepar/stern autopublish enabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
