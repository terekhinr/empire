#!/usr/bin/env python3
"""Пакетная генерация картинок из curated_topic_images_manifest.json.

  ./venv/bin/python tools/generate_curated_images_nanobanana.py --provider fal
  ./venv/bin/python tools/generate_curated_images_nanobanana.py --provider gemini
  ./venv/bin/python tools/generate_curated_images_nanobanana.py --channel stern --provider fal
  ./venv/bin/python tools/generate_curated_images_nanobanana.py --only STR-EV-001 --provider fal

Требует FAL_KEY (fal) или GEMINI_API_KEY (gemini) в .env / empire.env.
После генерации: ./venv/bin/python tools/apply_curated_images.py
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
sys.path.insert(0, str(ROOT / "tools"))

from curated_image_lib import (  # noqa: E402
    MANIFEST_PATH,
    channel_image_provider,
    gdepar_prompt_en,
    load_styles,
)

MIN_BYTES_OK = 25_000


def _resolve_provider(channel: str, cli: str, styles: dict) -> str:
    if cli != "auto":
        return cli
    return channel_image_provider(channel, styles)


def _resolve_prompt(it: dict, styles: dict, provider: str) -> str:
    ch = it.get("channel", "")
    if ch == "gdepar":
        return gdepar_prompt_en(
            it.get("topic_raw") or "",
            it.get("scene_en") or "",
            styles,
            provider=provider,
        )
    return it.get("prompt_en") or ""


def _api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY") or "").strip()


def _fal_key() -> str:
    return (os.getenv("FAL_KEY") or "").strip()


def _fal_image_size(aspect: str) -> str:
    a = (aspect or "4:3").strip()
    return {
        "4:3": "landscape_4_3",
        "3:4": "portrait_4_3",
        "16:9": "landscape_16_9",
        "9:16": "portrait_16_9",
        "1:1": "square_hd",
    }.get(a, "landscape_4_3")


def _fal_negative(channel: str, styles: dict) -> str:
    base = {
        "gdepar": (
            "household broom, witch broom, modern bathroom, shower, jacuzzi, spa hotel, gym, "
            "vehicle, neon lights, watermark, logo, text, cartoon, anime, visible face, portrait"
        ),
        "stern": (
            "anime, cartoon, bodybuilder, crossfit poster, neon, watermark, logo, text, "
            "visible face, portrait, selfie, distorted limbs, extra fingers"
        ),
    }.get(channel, "watermark, logo, text, cartoon, anime")
    ch = (styles.get("channels") or {}).get(channel) or {}
    extra = (ch.get("negative") or "").strip()
    return f"{base}, {extra}" if extra else base


def generate_fal_nanobanana_one(
    client: httpx.Client,
    *,
    fal_key: str,
    prompt: str,
    aspect: str,
) -> bytes | None:
    payload = {
        "prompt": prompt,
        "aspect_ratio": (aspect or "4:3").strip(),
        "output_format": "jpeg",
        "num_images": 1,
    }
    res = client.post(
        "https://fal.run/fal-ai/gemini-25-flash-image",
        headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180.0,
    )
    if res.status_code != 200:
        print(f"    fal-nb HTTP {res.status_code}: {(res.text or '')[:280]}")
        return None
    images = res.json().get("images") or []
    img_url = (images[0] or {}).get("url") if images else None
    if not img_url:
        print("    fal-nb: no image url")
        return None
    img_res = client.get(img_url, timeout=120.0)
    if img_res.status_code != 200:
        print(f"    fal-nb download HTTP {img_res.status_code}")
        return None
    return img_res.content


def generate_fal_one(
    client: httpx.Client,
    *,
    fal_key: str,
    prompt: str,
    aspect: str,
    negative: str,
) -> bytes | None:
    payload = {
        "prompt": prompt,
        "image_size": _fal_image_size(aspect),
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "negative_prompt": negative,
    }
    res = client.post(
        "https://fal.run/fal-ai/flux/dev",
        headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180.0,
    )
    if res.status_code != 200:
        print(f"    fal HTTP {res.status_code}: {(res.text or '')[:280]}")
        return None
    images = res.json().get("images") or []
    img_url = (images[0] or {}).get("url") if images else None
    if not img_url:
        print("    fal: no image url")
        return None
    img_res = client.get(img_url, timeout=120.0)
    if img_res.status_code != 200:
        print(f"    fal download HTTP {img_res.status_code}")
        return None
    return img_res.content


def _extract_inline_image(data: dict) -> bytes | None:
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    return None


def _save_jpeg(raw: bytes, dest: Path, quality: int = 92) -> None:
    from PIL import Image

    img = Image.open(BytesIO(raw))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (245, 242, 238))
        bg.paste(img, mask=img.split()[3])
        img = bg
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="JPEG", quality=quality, optimize=True)


def generate_one(
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
            "responseFormat": {"image": {"aspectRatio": aspect, "imageSize": image_size}},
        },
    }
    res = client.post(url, headers=headers, json=payload, timeout=120.0)
    if res.status_code != 200:
        payload_simple = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        res = client.post(url, headers=headers, json=payload_simple, timeout=120.0)
    if res.status_code != 200:
        print(f"    HTTP {res.status_code}: {(res.text or '')[:280]}")
        return None
    return _extract_inline_image(res.json())


def main() -> int:
    load_dotenv(ROOT / ".env")
    load_dotenv("/etc/empire/empire.env")

    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", choices=("stern", "gdepar", "all"), default="all")
    ap.add_argument("--only", action="append", default=[], help="topic_id, repeatable")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=2.5, help="пауза между запросами (quota)")
    ap.add_argument(
        "--provider",
        choices=("auto", "fal", "fal-nb", "gemini"),
        default="auto",
        help="auto=по каналу; fal=Flux; fal-nb=Nano Banana via Fal; gemini=Google API",
    )
    args = ap.parse_args()

    if not MANIFEST_PATH.is_file():
        print(f"Нет {MANIFEST_PATH} — сначала build_nanobanana_image_manifest.py")
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    items = [
        i
        for i in (manifest.get("items") or [])
        if not i.get("skip_nanobanana") and i.get("status") != "existing"
    ]
    if args.channel != "all":
        items = [i for i in items if i.get("channel") == args.channel]
    if args.only:
        only = set(args.only)
        items = [i for i in items if i.get("topic_id") in only]

    if not items:
        print("0 задач")
        return 1

    styles = load_styles()
    defaults = styles.get("defaults") or {}
    model = (os.getenv("CURATED_IMAGE_GEMINI_MODEL") or defaults.get("model") or "gemini-2.5-flash-image").strip()
    image_size = (os.getenv("CURATED_IMAGE_GEMINI_SIZE") or defaults.get("image_size") or "1K").strip()
    quality = int(defaults.get("jpeg_quality") or 92)

    if args.dry_run:
        for it in items[:5]:
            print(it["topic_id"], "→", it["output_file"])
        print(f"... total {len(items)}")
        return 0

    api_key = _api_key()
    fal_key = _fal_key()

    ok = skip = fail = 0
    status_by_key: dict[tuple[str, str], str] = {}
    with httpx.Client() as client:
        for it in items:
            tid = it.get("topic_id", "?")
            ch = it.get("channel", "")
            prov = _resolve_provider(ch, args.provider, styles)
            use_gemini = prov == "gemini"
            use_fal_nb = prov in ("fal-nb", "fal_nb")
            use_fal = prov == "fal"
            if (use_fal or use_fal_nb) and not fal_key:
                print(f"FAIL {tid}: FAL_KEY не задан")
                fail += 1
                continue
            if use_gemini and not api_key:
                print(f"FAIL {tid}: GEMINI_API_KEY не задан")
                fail += 1
                continue
            dest = ROOT / it["output_file"]
            if dest.is_file() and dest.stat().st_size >= MIN_BYTES_OK and not args.force:
                print(f"SKIP {tid} (exists)")
                status_by_key[(ch, tid)] = "exists"
                skip += 1
                continue
            aspect = it.get("aspect_ratio") or "4:3"
            prompt = _resolve_prompt(it, styles, prov)
            print(f"GEN  {tid} [{prov}] …")
            raw: bytes | None = None
            if use_fal_nb:
                raw = generate_fal_nanobanana_one(
                    client,
                    fal_key=fal_key,
                    prompt=prompt,
                    aspect=aspect,
                )
            elif use_gemini:
                raw = generate_one(
                    client,
                    api_key=api_key,
                    model=model,
                    prompt=prompt,
                    aspect=aspect,
                    image_size=image_size,
                )
            elif use_fal:
                raw = generate_fal_one(
                    client,
                    fal_key=fal_key,
                    prompt=prompt,
                    aspect=aspect,
                    negative=_fal_negative(ch, styles),
                )
            if not raw or len(raw) < MIN_BYTES_OK:
                print(f"FAIL {tid}")
                status_by_key[(ch, tid)] = "failed"
                fail += 1
            else:
                _save_jpeg(raw, dest, quality=quality)
                status_by_key[(ch, tid)] = "generated"
                print(f"OK   {tid} → {dest} ({dest.stat().st_size // 1024} KB)")
                ok += 1
            time.sleep(max(0.5, args.sleep))

    all_items = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for it in all_items.get("items") or []:
        key = (it.get("channel"), it.get("topic_id"))
        if key in status_by_key:
            it["status"] = status_by_key[key]
    all_items["items"] = all_items.get("items") or []
    MANIFEST_PATH.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done: ok={ok} skip={skip} fail={fail}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
