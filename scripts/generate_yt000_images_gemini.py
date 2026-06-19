#!/usr/bin/env python3
"""YT-000 B-roll: пакетная генерация PNG (Gemini flash-image / Imagen, fallback Fal Flux).

Конфиг: data/pension/video/graphics/yt-000/images_config.json
Выход:   data/pension/video/graphics/yt-000/images/

  ./venv/bin/python scripts/generate_yt000_images_gemini.py
  ./venv/bin/python scripts/generate_yt000_images_gemini.py --only IMG-14
  ./venv/bin/python scripts/generate_yt000_images_gemini.py --provider gemini
  ./venv/bin/python scripts/generate_yt000_images_gemini.py --provider fal
  ./venv/bin/python scripts/generate_yt000_images_gemini.py --provider auto
  ./venv/bin/python scripts/generate_yt000_images_gemini.py --dry-run
  ./venv/bin/python scripts/generate_yt000_images_gemini.py --force
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
GRAPHICS_DIR = ROOT / "data" / "pension" / "video" / "graphics" / "yt-000"
CONFIG_PATH = GRAPHICS_DIR / "images_config.json"
TARGET_W, TARGET_H = 1920, 1080
MIN_BYTES_OK = 40_000


def _api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY") or "").strip()


def _build_full_prompt(item: dict, cfg: dict) -> str:
    mode = (item.get("mode") or "A").upper()
    style = cfg["style_a"] if mode == "A" else cfg["style_b"]
    neg = cfg["negative_a"] if mode == "A" else cfg["negative_b"]
    return f"{item['prompt'].strip()} {style} {neg}"


def _save_png_bytes(raw: bytes, dest: Path) -> None:
    from PIL import Image

    img = Image.open(BytesIO(raw))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (13, 17, 23))
        bg.paste(img, mask=img.split()[3])
        img = bg
    w, h = img.size
    if w != TARGET_W or h != TARGET_H:
        img = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="PNG", optimize=True)


def _extract_inline_image(data: dict) -> bytes | None:
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if not inline:
                continue
            b64 = inline.get("data")
            if b64:
                return base64.b64decode(b64)
    return None


def _generate_flash_image(
    client: httpx.Client,
    *,
    api_key: str,
    model: str,
    prompt: str,
    aspect: str,
    image_size: str,
) -> bytes | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "responseFormat": {
                "image": {"aspectRatio": aspect, "imageSize": image_size},
            },
        },
    }
    res = client.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        payload_simple = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        res = client.post(url, headers=headers, json=payload_simple)
    if res.status_code != 200:
        print(f"    flash HTTP {res.status_code}: {(res.text or '')[:300]}")
        return None
    return _extract_inline_image(res.json())


def _fal_key() -> str:
    return (os.getenv("FAL_KEY") or "").strip()


def _generate_fal(http: httpx.Client, *, prompt: str) -> bytes | None:
    fal_key = _fal_key()
    if not fal_key:
        print("    fal: FAL_KEY не задан")
        return None
    negative = (
        "text, watermark, logo, signature, blurry, low quality, cartoon, anime, "
        "deformed hands, extra fingers, bright cheesy smile"
    )
    payload = {
        "prompt": prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "negative_prompt": negative,
    }
    res = http.post(
        "https://fal.run/fal-ai/flux/dev",
        headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180.0,
    )
    if res.status_code != 200:
        print(f"    fal HTTP {res.status_code}: {(res.text or '')[:300]}")
        return None
    images = res.json().get("images") or []
    img_url = (images[0] or {}).get("url") if images else None
    if not img_url:
        print("    fal: no image url")
        return None
    img_res = http.get(img_url, timeout=120.0)
    if img_res.status_code != 200:
        print(f"    fal download {img_res.status_code}")
        return None
    return img_res.content


def _generate_imagen(client, *, model: str, prompt: str, aspect: str) -> bytes | None:
    from google.genai import types

    config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio=aspect,
        output_mime_type="image/png",
    )
    try:
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=config,
        )
    except Exception as exc:
        print(f"    imagen error: {exc}")
        return None
    if not response.generated_images:
        print("    imagen: empty response")
        return None
    img = response.generated_images[0].image
    if img.image_bytes:
        return img.image_bytes
    return None


def _generate_one(
    http: httpx.Client,
    genai_client,
    *,
    api_key: str,
    cfg: dict,
    item: dict,
    dest: Path,
    force: bool,
    provider: str,
) -> bool:
    if dest.is_file() and dest.stat().st_size >= MIN_BYTES_OK and not force:
        print(f"  skip {item['id']} ({dest.name})")
        return True

    prompt = _build_full_prompt(item, cfg)
    aspect = cfg.get("aspect_ratio") or "16:9"
    image_size = (os.getenv("PENSION_YT000_IMAGE_SIZE") or cfg.get("image_size") or "2K").strip()
    model = (os.getenv("PENSION_YT000_IMAGE_MODEL") or cfg.get("model") or "gemini-2.5-flash-image").strip()
    fallback = (
        os.getenv("PENSION_YT000_IMAGEN_MODEL") or cfg.get("fallback_model") or "imagen-4.0-generate-001"
    ).strip()

    print(f"  gen {item['id']} → {dest.name} [{provider}]")
    raw: bytes | None = None

    use_gemini = provider in ("gemini", "auto")
    use_fal = provider in ("fal", "auto")

    if use_gemini and api_key:
        raw = _generate_flash_image(
            http,
            api_key=api_key,
            model=model,
            prompt=prompt,
            aspect=aspect,
            image_size=image_size,
        )
        if not raw and genai_client:
            print(f"    fallback imagen → {fallback}")
            raw = _generate_imagen(genai_client, model=fallback, prompt=prompt, aspect=aspect)
    elif use_gemini and not api_key:
        print("    gemini: нет GEMINI_API_KEY")

    if not raw and use_fal:
        print("    fallback fal flux/dev")
        raw = _generate_fal(http, prompt=prompt)

    if not raw:
        return False

    _save_png_bytes(raw, dest)
    kb = dest.stat().st_size // 1024
    print(f"  ok {item['id']} ({kb} KB)")
    return kb >= 30


def main() -> int:
    parser = argparse.ArgumentParser(description="YT-000 images via Gemini")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--only", metavar="IMG-01", help="один id из конфига")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay", type=float, default=4.0, help="пауза между запросами (сек)")
    parser.add_argument(
        "--provider",
        choices=("gemini", "fal", "auto"),
        default="gemini",
        help="gemini — только API Google; fal — только Flux; auto — gemini, затем fal",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    out_dir = GRAPHICS_DIR / cfg.get("output_dir", "images")
    images = cfg["images"]
    if args.only:
        images = [i for i in images if i["id"] == args.only]
        if not images:
            print(f"Неизвестный id: {args.only}", file=sys.stderr)
            return 1

    if args.dry_run:
        for item in images:
            print(f"\n=== {item['id']} ({item['file']}) mode={item.get('mode')} ===")
            print(_build_full_prompt(item, cfg)[:500], "…")
        return 0

    key = _api_key()
    if args.provider in ("gemini", "auto") and not key:
        print("GEMINI_API_KEY не задан в .env", file=sys.stderr)
        return 1
    if args.provider in ("fal", "auto") and not _fal_key():
        print("FAL_KEY не задан в .env (нужен для --provider fal/auto)", file=sys.stderr)
        return 1

    genai_client = None
    if key and args.provider in ("gemini", "auto"):
        try:
            from google import genai

            genai_client = genai.Client(api_key=key)
        except Exception as exc:
            print(f"warn: google.genai недоступен ({exc}), только flash-image")

    ok = 0
    with httpx.Client(timeout=180.0) as http:
        for idx, item in enumerate(images):
            dest = out_dir / item["file"]
            if _generate_one(
                http,
                genai_client,
                api_key=key,
                cfg=cfg,
                item=item,
                dest=dest,
                force=args.force,
                provider=args.provider,
            ):
                ok += 1
            if idx < len(images) - 1 and args.delay > 0:
                time.sleep(args.delay)

    print(f"\nГотово: {ok}/{len(images)} → {out_dir}")
    return 0 if ok == len(images) else 1


if __name__ == "__main__":
    raise SystemExit(main())
