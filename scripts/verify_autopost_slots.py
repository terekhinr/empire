#!/usr/bin/env python3
"""Сквозная проверка: матрица → resolve → тело/картинка по правилам канала."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MSK = ZoneInfo("Europe/Moscow")


async def main() -> int:
    import gdepar_content
    import garden_content
    import lenin_content
    import stern_content
    from gdepar_duo_curated import _publishable as duo_ok
    from gdepar_mono_curated import _publishable as mono_ok
    from stern_curated import _publishable as stern_ok

    cfg = json.loads((ROOT / "content_config.json").read_text(encoding="utf-8"))
    now = datetime.now(MSK)
    print(f"now MSK {now.isoformat()}")
    print(f"mono publishable: {sum(1 for e in json.loads((ROOT/'data/gdepar_mono_curated.json').read_text())['entries'] if mono_ok(e))}")
    print(f"duo publishable: {sum(1 for e in json.loads((ROOT/'data/gdepar_duo_curated.json').read_text())['entries'] if duo_ok(e))}")
    print(f"excerpts: {len(json.loads((ROOT/'data/gdepar_book_excerpts.json').read_text())['entries'])}")
    print(
        f"stern publishable: {sum(1 for e in json.loads((ROOT/'data/stern_curated.json').read_text())['entries'] if stern_ok(e))}"
    )

    errors: list[str] = []
    checks = 0

    async def check(persona: str, when: datetime, time_str: str) -> None:
        nonlocal checks
        slot = (cfg.get(persona) or {}).get("topics", {}).get(str(when.weekday()), {}).get(time_str)
        if not slot:
            return
        checks += 1
        if persona == "gdepar":
            topic, body, img = await gdepar_content.resolve_gdepar_slot(
                slot, resolve_topic_fn=lambda *_: asyncio.sleep(0, result="x")
            )
            seed = None
        elif persona == "stern":
            topic, body, img, seed = await stern_content.resolve_stern_slot(
                slot, weekday=when.weekday(), resolve_topic_fn=lambda *_: asyncio.sleep(0, result="x")
            )
        elif persona == "lenin":
            topic, body, img, seed = await lenin_content.resolve_lenin_slot(
                slot, weekday=when.weekday(), recent_bodies=[]
            )
        elif persona == "garden":
            topic, body, img, seed = await garden_content.resolve_garden_slot(
                slot, resolve_topic_fn=lambda *_: asyncio.sleep(0, result="x")
            )
        else:
            return

        blen = len((body or "").strip())
        stype = slot.get("type") if isinstance(slot, dict) else slot
        print(f"\n[{persona}] {when.strftime('%a')} {time_str} type={stype}")
        print(f"  topic: {(topic or '')[:90]}")
        print(f"  body: {blen} chars | img: {img or '—'}")
        if seed:
            print(f"  seed: kind={seed.get('_kind')} visual={seed.get('visual_query') or seed.get('image_prompt_en','')!s}"[:120])

        if not body or body.startswith("🛑") or "пуста" in (body or "").lower() and "очередь" in (body or "").lower():
            # empty queue is error for live slots
            if "fallback" in (topic or "").lower() or "пуста" in (body or ""):
                errors.append(f"{persona} {time_str}: empty/fallback queue")
        if persona == "stern" and stype == "stern_curated":
            if not img or not Path(img).is_file() and not (ROOT / str(img)).is_file():
                errors.append(f"stern {time_str}: no image file for curated")
        if persona == "garden" and stype == "garden_curated":
            if not img and not (seed or {}).get("image_prompt_en"):
                errors.append(f"garden {time_str}: no image and no fal prompt")
        if persona == "lenin" and stype == "lenin_rubric":
            tag = topic or ""
            if "[Ленин в искусстве]" in tag or "[Ленин в кино]" in tag:
                if img and ("1917" in str(img) or "_default_lenin" in str(img)):
                    errors.append(f"lenin {time_str}: generic Lenin portrait for art/cinema")
                if not img and not (seed or {}).get("visual_query"):
                    errors.append(f"lenin {time_str}: no image and no visual_query")
        if persona == "gdepar" and stype == "mono_curated":
            if "[Монолог]" not in (topic or "") and "fallback" in (topic or "").lower():
                errors.append(f"gdepar {time_str}: mono fallback")

    # Check next 7 days all configured slots (resolve only — no publish)
    for day_off in range(7):
        day = now + timedelta(days=day_off)
        day = day.replace(hour=12, minute=0, second=0, microsecond=0)
        for persona in ("gdepar", "stern", "lenin", "garden"):
            bucket = (cfg.get(persona) or {}).get("topics", {}).get(str(day.weekday()), {})
            for time_str in sorted(bucket.keys()):
                try:
                    await check(persona, day, time_str)
                except Exception as exc:
                    errors.append(f"{persona} {time_str}: EXC {type(exc).__name__}: {exc}")
                    print(f"  EXC {exc}")

    print(f"\n=== checks={checks} errors={len(errors)} ===")
    for e in errors:
        print("ERR:", e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
