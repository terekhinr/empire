#!/usr/bin/env python3
"""4 сцены pension через Gemini API (Veo 3.1). Без fal.ai.

Конфиг: data/pension/video/scenes_4.json
Референс персонажа: data/pension/video/iosif_boroda_ref.png

  python scripts/generate_pension_video_gemini.py --only 01_laptop
  python scripts/generate_pension_video_gemini.py
  python scripts/generate_pension_video_gemini.py --concat-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "data" / "pension" / "video"
CONFIG_PATH = VIDEO_DIR / "scenes_4.json"
REF_PORTRAIT = VIDEO_DIR / "iosif_boroda_ref.png"

CHARACTER_HINT = (
    "The bearded man has a thick ginger beard, olive green baseball cap with white "
    "letters PENS, and a black t-shirt (Iosif Boroda)."
)
STYLE_HINT = (
    "2D minimalist cartoon animation, simple black line art on a solid white background, "
    "flat colors, editorial comic style, no photorealism."
)
NEGATIVE = (
    "photorealistic, 3d render, photograph, anime, gradient background, "
    "detailed textures, watermark, text on signs"
)


def _gemini_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY") or "").strip()


def _veo_model() -> str:
    return (
        os.getenv("PENSION_VEO_MODEL") or "veo-3.1-generate-preview"
    ).strip()


def _supports_reference_images(model: str) -> bool:
    return "lite" not in model.lower()


def _load_ref_image():
    from google.genai import types

    data = REF_PORTRAIT.read_bytes()
    return types.Image(image_bytes=data, mime_type="image/png")


def _reference_images():
    from google.genai import types

    img = _load_ref_image()
    return [
        types.VideoGenerationReferenceImage(
            image=img,
            reference_type=types.VideoGenerationReferenceType.ASSET,
        )
    ]


def _build_prompt(scene_prompt: str, *, with_character: bool) -> str:
    parts = [STYLE_HINT, scene_prompt]
    if with_character:
        parts.append(CHARACTER_HINT)
    parts.append("Smooth simple animation, consistent line weight throughout.")
    return " ".join(parts)


def _duration_for_scene(scene: dict, *, use_reference: bool) -> int:
    if use_reference:
        return 8  # Veo 3.1: reference_images require 8s
    raw = int(scene.get("duration_sec") or 6)
    if raw <= 4:
        return 4
    if raw <= 6:
        return 6
    return 8


def _generate_scene(client, scene: dict, dest: Path, *, force: bool) -> bool:
    from google.genai import types

    if dest.is_file() and dest.stat().st_size > 50000 and not force:
        print(f"  skip {scene['id']} (exists)")
        return True

    sid = scene["id"]
    model = _veo_model()
    character_scene = sid != "03_pov_crowd"
    use_ref_img = (
        character_scene
        and REF_PORTRAIT.is_file()
        and _supports_reference_images(model)
    )
    prompt = _build_prompt(scene["prompt"], with_character=character_scene)
    duration = _duration_for_scene(scene, use_reference=use_ref_img)

    config_kw: dict = {
        "aspect_ratio": "16:9",
        "duration_seconds": duration,
    }
    if use_ref_img:
        config_kw["reference_images"] = _reference_images()

    print(f"  veo {sid} model={model} duration={duration}s ref_img={use_ref_img}")
    try:
        operation = client.models.generate_videos(
            model=_veo_model(),
            prompt=prompt,
            config=types.GenerateVideosConfig(**config_kw),
        )
    except Exception as exc:
        err = str(exc)
        print(f"  FAIL start {sid}: {err}")
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            print(
                "  Квота Veo исчерпана для GEMINI_API_KEY. Проверьте лимиты: "
                "https://ai.dev/rate-limit — видео и картинки считаются отдельно.",
                file=sys.stderr,
            )
        return False

    while not operation.done:
        print(f"  … waiting {sid}")
        time.sleep(12)
        try:
            operation = client.operations.get(operation)
        except Exception as exc:
            print(f"  FAIL poll {sid}: {exc}")
            return False

    if getattr(operation, "error", None):
        print(f"  FAIL {sid}: {operation.error}")
        return False

    response = operation.response
    if not response or not response.generated_videos:
        print(f"  FAIL {sid}: empty response")
        return False

    video = response.generated_videos[0].video
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        client.files.download(file=video)
        video.save(str(dest))
    except Exception as exc:
        print(f"  FAIL save {sid}: {exc}")
        return False

    print(f"  ok {sid} → {dest} ({dest.stat().st_size // 1024} KB)")
    return True


def _postprocess(scene: dict, raw: Path, out: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_pension_demo_video import (
        _overlay_monitor_text,
        _overlay_signs,
    )

    overlays_dir = VIDEO_DIR / "overlays_gemini"
    if scene.get("sign_overlays"):
        tuples = [tuple(x) for x in scene["sign_overlays"]]
        _overlay_signs(raw, tuples, out, overlays_dir)
    elif scene.get("monitor_text_at_sec") is not None:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        text = cfg.get("monitor_text", "НА ПЕНСИЮ НИКОГДА!")
        _overlay_monitor_text(
            raw, text, float(scene["monitor_text_at_sec"]), out, overlays_dir
        )
    else:
        out.write_bytes(raw.read_bytes())


def _concat(clips: list[Path], out: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_pension_demo_video import _concat_clips

    _concat_clips(clips, out, fade_out=1.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pension 4 scenes via Gemini Veo")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--only", metavar="ID")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--concat-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="показать промпты без вызова API")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    scenes = cfg["scenes"]
    if args.only:
        scenes = [s for s in scenes if s["id"] == args.only]
        if not scenes:
            print(f"Неизвестная сцена: {args.only}", file=sys.stderr)
            return 1

    clips_raw = VIDEO_DIR / "clips_gemini"
    clips_final = VIDEO_DIR / "clips_gemini_final"
    clips_raw.mkdir(parents=True, exist_ok=True)
    clips_final.mkdir(parents=True, exist_ok=True)

    if args.concat_only:
        clips = [clips_final / f"{s['id']}.mp4" for s in cfg["scenes"]]
        missing = [c for c in clips if not c.is_file()]
        if missing:
            print("Нет клипов:", ", ".join(p.name for p in missing), file=sys.stderr)
            return 1
        out = VIDEO_DIR / "pension_4scenes_gemini.mp4"
        _concat(clips, out)
        print(f"FINAL → {out}")
        return 0

    key = _gemini_key()
    if not key:
        print("GEMINI_API_KEY не задан в .env", file=sys.stderr)
        return 1

    if args.dry_run:
        for scene in scenes:
            use_ref = scene["id"] != "03_pov_crowd"
            print(f"\n=== {scene['id']} ===")
            print(_build_prompt(scene["prompt"], with_character=use_ref))
            print(f"duration={_duration_for_scene(scene, use_reference=use_ref)} ref={use_ref}")
        return 0

    from google import genai

    client = genai.Client(api_key=key)

    ok = 0
    final_clips: list[Path] = []
    for scene in scenes:
        sid = scene["id"]
        print(f"\n=== {sid} ===")
        raw = clips_raw / f"{sid}.mp4"
        final = clips_final / f"{sid}.mp4"
        if _generate_scene(client, scene, raw, force=args.force):
            _postprocess(scene, raw, final)
            final_clips.append(final)
            ok += 1

    if ok == len(scenes) and len(scenes) == len(cfg["scenes"]) and not args.only:
        out = VIDEO_DIR / "pension_4scenes_gemini.mp4"
        print(f"\n=== concat {ok} ===")
        _concat(final_clips, out)
        print(f"FINAL → {out}")

    return 0 if ok == len(scenes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
