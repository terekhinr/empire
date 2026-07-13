#!/usr/bin/env python3
"""Собрать snegiri_kb/comic_briefs_data.json из program_data + comic_phases."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from snegiri_kb.program_data import EXERCISES  # noqa: E402

PHASES_JSON = ROOT / "snegiri_kb" / "comic_phases_data.json"
OUT = ROOT / "snegiri_kb" / "comic_briefs_data.json"

CAMERA_MAP = {
    "side": "side_90",
    "front": "front_45",
}

ONE_ARM = {
    "one_arm_swing",
    "hand_switch",
    "clean",
    "press",
    "push_press",
    "high_pull",
    "snatch",
    "jerk",
    "tgu_partial",
    "tgu_full",
}

ERROR_ZONE = {
    "curl_up": "шея / подбородок",
    "side_plank": "таз",
    "bird_dog": "таз",
    "pallof_press": "таз",
    "plank_shoulder_tap": "таз",
    "suitcase_carry": "наклон корпуса к гире",
    "farmer_walk": "плечи / трапеции",
    "hip_hinge": "поясница",
    "dead_stop": "момент касания внизу",
    "goblet_squat": "пятки",
    "halo": "траектория гири у головы",
    "rack_hold": "локти",
    "swing": "поясница",
    "one_arm_swing": "ротация корпуса",
    "hand_switch": "момент перехвата",
    "clean": "предплечье",
    "front_squat": "локти",
    "press": "поясница",
    "push_press": "колени / ноги",
    "tgu_partial": "локоть",
    "tgu_full": "дрейф гири",
    "high_pull": "корпус",
    "snatch": "локоть",
    "jerk": "локоть",
    "complex": "стойка / локти",
}


def equipment_for(slug: str) -> dict:
    if slug in ("curl_up", "side_plank", "bird_dog", "plank_shoulder_tap"):
        return {"kettlebell_count": 0, "weight_kg": None, "grip": None, "extra": ["mat"]}
    if slug == "pallof_press":
        return {"kettlebell_count": 0, "weight_kg": None, "grip": None, "extra": ["resistance_band"]}
    if slug == "suitcase_carry":
        return {"kettlebell_count": 1, "weight_kg": 16, "grip": "one_hand_right", "extra": []}
    if slug == "farmer_walk":
        # Базовый курс: одна гиря (правая). Две — tier advanced, см. advanced_variant.
        return {"kettlebell_count": 1, "weight_kg": 16, "grip": "one_hand_right", "extra": []}
    if slug == "halo":
        return {"kettlebell_count": 1, "weight_kg": 12, "grip": "two_hand_horns", "extra": []}
    if slug == "swing":
        return {"kettlebell_count": 1, "weight_kg": 16, "grip": "two_hand", "extra": []}
    if slug in ("goblet_squat", "front_squat", "complex"):
        return {"kettlebell_count": 1, "weight_kg": 16, "grip": "goblet_or_rack", "extra": []}
    if slug in ONE_ARM:
        return {"kettlebell_count": 1, "weight_kg": 16, "grip": "one_hand_right", "extra": []}
    return {"kettlebell_count": 1, "weight_kg": 16, "grip": "two_hand", "extra": []}


def location_for(track: str) -> str:
    # v2: эталон в industrial gym; A/B с home_room — см. comic_strategy_v2.md
    return "industrial_gym"


ADVANCED_VARIANTS: dict[str, dict] = {
    "farmer_walk": {
        "tier": "advanced",
        "name_ru_suffix": " (две гири)",
        "unlock_note": "После фазы S / при наличии 2-й гири 16 кг",
        "equipment": {
            "kettlebell_count": 2,
            "weight_kg": 16,
            "grip": "one_per_hand",
            "extra": [],
        },
        "working_side": None,
        "panel_script": [
            "стоя, по одной гире 16 кг в каждой руке, плечи опущены",
            "шаг вперёд, корпус вертикален, взгляд вперёд",
            "ОШИБКА: плечи подняты к ушам, шарканье",
        ],
        "output_suffix": "_2kb",
    },
}


def panel_script(slug: str, labels: list[str]) -> list[str]:
    """Краткое описание действия в каждой панели для промпта."""
    scripts: dict[str, list[str]] = {
        "curl_up": [
            "лёжа на коврике, руки под поясницей",
            "выдох, подъём грудной клетки, шея нейтральна",
            "пауза 2 сек, поясница на коврике",
            "ОШИБКА: подъём шеей и подбородком",
        ],
        "swing": [
            "hip hinge назад, две руки на гире 16 кг между ног",
            "подрыв таза и колен, импульс от бёдер",
            "гиря в полёте по дуге, корпус жёсткий",
            "верхняя точка: гиря уровень груди, корпус вертикален",
            "ОШИБКА: прогиб в пояснице",
        ],
        "halo": [
            "стоя, гиря 12 кг обе руки на рогах у подбородка",
            "ведёт гирю по кругу вокруг головы, близко к черепу",
            "ОШИБКА: гиря далеко от головы",
        ],
        "clean": [
            "замах hinge, одна гиря 16 кг в правой руке",
            "подрыв таза",
            "заброс на грудь в стойку, локоть прижат",
            "фиксация в стойке",
            "ОШИБКА: удар по предплечью",
        ],
        "suitcase_carry": [
            "стоя, одна гиря 16 кг в правой руке у бедра, корпус строго вертикален",
            "шаг вперёд, плечи на одном уровне, не наклоняться к гире",
            "ОШИБКА: наклон корпуса к гире",
        ],
        "rack_hold": [
            "стойка: гиря на груди, локти прижаты к корпусу, запястье прямое (Алферова)",
            "вид спереди: треугольник локти–запястья–гира, локти НЕ в стороны",
            "ОШИБКА: локти отведены в стороны, гиря уезжает вперёд",
        ],
        "jerk": [
            "стойка: локоть на подвздошную кость, предплечье на корпусе, не «крылья»",
            "лёгкий присед dip, стойка сохранена",
            "подрыв ногами, гиря взлетает",
            "фиксация: руки прямые над головой",
            "ОШИБКА: отжим от груди — локоть сгибается снова",
        ],
        "farmer_walk": [
            "стоя, одна гиря 16 кг в правой руке, корпус вертикален (база: одна гиря)",
            "шаг вперёд, осанка, плечи опущены",
            "ОШИБКА: провисание плеч / шарканье",
        ],
    }
    if slug in scripts:
        return scripts[slug]
    return [f"панель {i + 1}: {labels[i]}" for i in range(len(labels))]


def main() -> None:
    phases_data = json.loads(PHASES_JSON.read_text(encoding="utf-8"))
    briefs: dict = {
        "_meta": {
            "version": 1,
            "spec": "docs/snegiri_comic_spec_v1.md",
            "ab_tests": "docs/snegiri_comic_ab_tests.md",
            "defaults": {
                "location": "industrial_gym",
                "location_ab_alt": "home_room",
                "working_hand": "right",
                "f_from_m_reference": True,
                "labels_language": "ru_caps",
                "equipment_tier_default": "base",
                "kettlebells_base": "1x16kg (+ mat, band S4; halo 12kg)",
                "kettlebells_advanced": "2x16kg where advanced_variant exists",
            },
            "note": "Канон для промптов Gemini/Cursor. status: needs_regen до QA.",
        }
    }

    for eid, ex in sorted(EXERCISES.items(), key=lambda x: x[0]):
        slug = ex["slug"]
        spec = phases_data.get(slug)
        if not spec:
            continue
        labels = [p["term"].upper() for p in spec["phases"]]
        track = ex["track"]
        briefs[slug] = {
            "id": eid,
            "name_ru": spec["name"],
            "track": track,
            "tier": "base",
            "panels": spec["panels"],
            "camera": CAMERA_MAP.get(ex["camera"], ex["camera"]),
            "camera_hint": ex["hint"],
            "location": location_for(track),
            "equipment": equipment_for(slug),
            "working_side": (
                "right"
                if slug in ONE_ARM or slug in ("suitcase_carry", "farmer_walk")
                else None
            ),
            "labels_ru": labels,
            "panel_script": panel_script(slug, labels),
            "error_zone": ERROR_ZONE.get(slug, "зона ошибки"),
            "output": {
                "m": f"assets/comics/{slug}_m.webp",
                "f": f"assets/comics/{slug}_f.webp",
                "frames": f"assets/comics/frames/{slug}",
            },
            "f_derived_from_m": True,
            "status": "needs_regen",
            "qa_notes": "",
        }
        if slug in ADVANCED_VARIANTS:
            adv = ADVANCED_VARIANTS[slug]
            suf = adv["output_suffix"]
            briefs[slug]["advanced_variant"] = {
                **adv,
                "labels_ru": labels,
                "panel_script": adv.get("panel_script") or panel_script(slug, labels),
                "error_zone": ERROR_ZONE.get(slug, "зона ошибки"),
                "output": {
                    "m": f"assets/comics/{slug}{suf}_m.webp",
                    "f": f"assets/comics/{slug}{suf}_f.webp",
                    "frames": f"assets/comics/frames/{slug}{suf}",
                },
                "status": "needs_regen",
            }

    OUT.write_text(json.dumps(briefs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK {len(briefs) - 1} briefs → {OUT}")


if __name__ == "__main__":
    main()
