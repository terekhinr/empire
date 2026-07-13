#!/usr/bin/env python3
"""Рендер промпта для Gemini или Cursor из comic_briefs_data.json."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEFS = ROOT / "snegiri_kb" / "comic_briefs_data.json"

LOCATION_EN = {
    "industrial_gym": (
        "INDUSTRIAL GYM: concrete floor, metal walls, dramatic shadows, empty professional "
        "training space. NO barbells, NO plate stacks, NO squat racks in frame. "
        "NO foreign gym logos on walls. Optional faint Snegiri bird stencil far background only."
    ),
    "home_garage": (
        "HOME GARAGE: bare concrete floor, empty dark space, no furniture, "
        "no gym equipment visible"
    ),
    "home_room": (
        "HOME ROOM: dark wall, black exercise mat on floor, minimal empty space, "
        "no gym equipment visible"
    ),
}

CAMERA_EN = {
    "side_90": "camera strictly 90° side view",
    "front_45": "camera front 45° angle",
}

FORBIDDEN = (
    "FORBIDDEN ON IMAGE: barbell, barbell plates, squat rack, power rack, "
    "cable machine, bench press, dumbbells, commercial gym brand logos, "
    "StrongFirst logos, motivational posters with faces. "
    "ONLY approved equipment listed below."
)

MERCH = (
    "ATHLETE CLOTHING: black t-shirt with white line-art bullfinch-on-kettlebell logo "
    "on chest (8-10cm). Black shorts or leggings, NO other logos. "
    "All panel labels in RUSSIAN Cyrillic only."
)


def equipment_text(eq: dict) -> str:
    n = eq["kettlebell_count"]
    if n == 0:
        extra = ", ".join(eq.get("extra") or []) or "bodyweight only"
        return f"No kettlebell. Equipment: {extra}."
    w = eq["weight_kg"]
    grip = eq["grip"] or "standard"
    if n == 2:
        return f"EXACTLY TWO identical {w}kg cast iron kettlebells, one in each hand."
    if grip == "two_hand":
        return f"EXACTLY ONE {w}kg cast iron kettlebell, BOTH hands on handle."
    if grip == "two_hand_horns":
        return f"EXACTLY ONE {w}kg kettlebell, BOTH hands on horns near chin."
    if grip == "one_hand_right":
        return f"EXACTLY ONE {w}kg kettlebell in RIGHT hand only. Left hand empty."
    if grip == "goblet_or_rack":
        return f"EXACTLY ONE {w}kg kettlebell at chest (goblet or rack position)."
    return f"EXACTLY ONE {w}kg kettlebell. Grip: {grip}."


def performer_text(performer: str) -> str:
    if performer == "f":
        return "athletic woman age 35, black leggings, black t-shirt"
    return "athletic man age 35, black shorts, black t-shirt"


def build_prompt(
    brief: dict,
    performer: str,
    *,
    ab_location: str | None = None,
    tier: str = "base",
) -> str:
    slug = brief.get("_slug", "")
    if tier == "advanced":
        adv = brief.get("advanced_variant")
        if not adv:
            raise ValueError(f"no advanced_variant for {slug}")
        brief = {**brief, **adv, "_slug": slug, "_tier": "advanced"}
    else:
        brief = {**brief, "_tier": "base"}

    loc = ab_location or brief["location"]
    labels = brief["labels_ru"]
    panels = brief["panels"]
    script = brief.get("panel_script") or labels

    tier_note = ""
    if brief.get("_tier") == "advanced":
        tier_note = "TIER: ADVANCED (two kettlebells course extension). "
    elif brief["equipment"].get("kettlebell_count") == 1:
        tier_note = "TIER: BASE — EXACTLY ONE kettlebell in entire strip. "

    panel_lines = []
    for i in range(panels):
        lbl = labels[i] if i < len(labels) else f"PANEL {i+1}"
        act = script[i] if i < len(script) else lbl
        panel_lines.append(f"Panel {i+1} label «{lbl}»: {act}")

    out_suffix = ""
    if brief.get("_tier") == "advanced":
        out_m = brief.get("output", {}).get("m", "")
        if "_2kb_" in out_m:
            out_suffix = "_2kb"

    ref_block = ""
    if performer == "f" and brief.get("f_derived_from_m"):
        ref_name = f"{slug}{out_suffix}_m.webp"
        ref_block = (
            f"\nREFERENCE: attach approved {ref_name}. "
            "Repeat THE SAME panel choreography, SAME kettlebell count, SAME working hand, "
            "SAME camera. Only change athlete to woman."
        )

    out_file = f"{slug}{out_suffix}_{performer}.webp"

    return f"""Horizontal 1920×1080 brutalist fitness comic strip, {panels} equal panels left to right.
Pure black background #000000. High contrast black and white photo aesthetic.
White CV skeleton overlay on athlete. Black t-shirt with white line-art bullfinch-on-kettlebell logo on chest.

{tier_note}{FORBIDDEN}

{MERCH}

LOCATION: {LOCATION_EN.get(loc, loc)}
{equipment_text(brief['equipment'])}
CAMERA: {CAMERA_EN.get(brief['camera'], brief['camera'])}.
ATHLETE: {performer_text(performer)}.
{brief.get('working_side') and f'Working hand: RIGHT only.' or ''}

PANELS (labels MUST be exact Russian text on image, IBM Plex Mono style caps):
{chr(10).join(panel_lines)}

Last panel if ERROR: single bright red #FF3300 CV error line on {brief['error_zone']}.
No English text — all labels Cyrillic.
No watermark. No color except #FF3300 on error panel.
Output file: {out_file}
{ref_block}"""


def master_prompt_gemini() -> str:
    return """Ты — арт-директор snegirinegiri.ru («Снегири не гири»).

ПРОДУКТ: домашние тренировки. Базовый курс: коврик + ОДНА гиря 16 кг на все упражнения.
Продвинутый tier (2 гири) — отдельные эталоны, только где есть advanced_variant в brief.
ЗАПРЕТ: штанга, блины, стойки, тренажёры, «зал с окнами».

ПАЛИТРА: #000000 фон · #FFFFFF тело/гиря/скелет · #FF3300 ТОЛЬКО линия ERROR.

ПОРЯДОК РАБОТЫ:
1. Сначала M (мужчина) по brief — одно упражнение.
2. После QA — F (женщина) С РЕФЕРЕНСОМ утверждённого M, та же хореография.

Подписи панелей — ТОЛЬКО русский из brief (labels_ru). Без ST/DRIVE/TOP.

Прикрепи hero-poster.png как стиль. Жди brief следующим сообщением."""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--performer", choices=("m", "f"), default="m")
    parser.add_argument("--tier", choices=("base", "advanced"), default="base")
    parser.add_argument("--ab-location", choices=("industrial_gym", "home_garage", "home_room"))
    parser.add_argument("--master", action="store_true", help="print Gemini session opener")
    parser.add_argument("--json", action="store_true", help="output JSON bundle")
    args = parser.parse_args()

    if args.master:
        print(master_prompt_gemini())
        return

    data = json.loads(BRIEFS.read_text(encoding="utf-8"))
    brief = data.get(args.slug)
    if not brief:
        raise SystemExit(f"unknown slug: {args.slug}")

    brief = {**brief, "_slug": args.slug}
    prompt = build_prompt(
        brief, args.performer, ab_location=args.ab_location, tier=args.tier
    )

    if args.json:
        print(
            json.dumps(
                {
                    "slug": args.slug,
                    "performer": args.performer,
                    "ab_location": args.ab_location,
                    "prompt": prompt,
                    "references": (
                        [brief["output"]["m"]]
                        if args.performer == "f"
                        else ["assets/hero-poster.png"]
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(prompt)


if __name__ == "__main__":
    main()
