#!/usr/bin/env python3
"""Генерация иллюстраций к книге «На пенсию НИКОГДА» (Fal Flux dev, 16:9)."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "pension" / "illustrations"

# --ar 16:9 из Midjourney убираем — размер задаём через image_size
_AR_SUFFIX = re.compile(r"\s*--ar\s+[\d:]+", re.I)

ILLUSTRATIONS: list[tuple[str, str, str]] = [
    (
        "01_fire_illusion",
        "Иллюзия ранней пенсии (FIRE)",
        "Cinematic wide shot of an elderly but fit couple walking on a pristine tropical beach at sunset, holding hands, golden hour lighting, hyper-realistic, advertising style, bright and unnaturally perfect colors, 8k resolution",
    ),
    (
        "02_demographic_ponzi",
        "Демографическое Понци (Перевернутая пирамида)",
        "A futuristic holographic population pyramid chart glowing in neon red and blue colors, flipping upside down, dark cyberpunk background, high tech data visualization, 8k, photorealistic",
    ),
    (
        "03_turkey_error",
        "Ошибка Индейки (Иллюзия безопасности)",
        "Close up POV shot from a fat turkey looking at a farmer holding a bucket of grain, sunny idyllic farm, dramatic foreshadowing shadows, hyper-detailed, cinematic lighting",
    ),
    (
        "04_digital_escapism",
        "Эскапизм и цифровое одиночество",
        "A massive crowd of people standing in a dark neon-lit subway station, every single person is looking down at a glowing smartphone screen, cold blue and purple lighting, dystopian atmosphere, cinematic, 8k",
    ),
    (
        "05_inflation_money_press",
        "Инфляция и сгорание денег",
        "Macro shot of a massive industrial printing press rapidly printing endless sheets of paper money, motion blur on the paper, dark and dramatic factory lighting, financial crisis concept, photorealistic",
    ),
]

NEGATIVE = (
    "text, watermark, logo, signature, blurry, low quality, cartoon, anime, "
    "deformed hands, extra fingers"
)


def _clean_prompt(prompt: str) -> str:
    return _AR_SUFFIX.sub("", prompt).strip()


async def _generate_one(
    client: httpx.AsyncClient,
    fal_key: str,
    slug: str,
    prompt: str,
    dest: Path,
    *,
    force: bool,
) -> bool:
    if dest.is_file() and dest.stat().st_size > 8000 and not force:
        print(f"skip {slug} ({dest.name})")
        return True

    payload = {
        "prompt": _clean_prompt(prompt),
        "image_size": "landscape_16_9",
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "negative_prompt": NEGATIVE,
    }
    res = await client.post(
        "https://fal.run/fal-ai/flux/dev",
        headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120.0,
    )
    if res.status_code != 200:
        print(f"FAIL {slug}: fal {res.status_code} {res.text[:300]}")
        return False

    images = res.json().get("images") or []
    img_url = (images[0] or {}).get("url") if images else None
    if not img_url:
        print(f"FAIL {slug}: no image url in response")
        return False

    img_res = await client.get(img_url, timeout=120.0)
    img_res.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(img_res.content)
    print(f"ok   {slug} → {dest} ({len(img_res.content) // 1024} KB)")
    return True


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="перегенерировать даже если файл есть")
    parser.add_argument("--only", metavar="SLUG", help="только один slug, напр. 03_turkey_error")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    fal_key = (os.getenv("FAL_KEY") or "").strip()
    if not fal_key:
        print("FAL_KEY не задан в .env", file=sys.stderr)
        return 1

    items = ILLUSTRATIONS
    if args.only:
        items = [t for t in ILLUSTRATIONS if t[0] == args.only]
        if not items:
            print(f"Неизвестный slug: {args.only}", file=sys.stderr)
            return 1

    ok, fail = 0, 0
    async with httpx.AsyncClient() as client:
        for slug, _title, prompt in items:
            dest = OUT_DIR / f"{slug}.jpg"
            if await _generate_one(client, fal_key, slug, prompt, dest, force=args.force):
                ok += 1
            else:
                fail += 1

    manifest = OUT_DIR / "manifest.json"
    import json

    manifest.write_text(
        json.dumps(
            [
                {"slug": s, "title": t, "file": f"{s}.jpg", "prompt": _clean_prompt(p)}
                for s, t, p in ILLUSTRATIONS
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n{ok} ok, {fail} fail → {OUT_DIR}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
