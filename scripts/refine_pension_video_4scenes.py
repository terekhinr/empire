#!/usr/bin/env python3
"""4 сцены pension: нарезка исходника → Kling O3 video-to-video edit → монтаж.

КУДА КЛАСТЬ ИСХОДНОЕ ВИДЕО
-------------------------
  data/pension/video/source/<любое>.mp4
  или укажите путь: --source path/to/video.mp4

Скрипт сам загрузит фрагменты на CDN fal (fal_client.upload_file).
Вручную в UI: https://fal.ai/models/fal-ai/kling-video/o3/pro/video-to-video/edit
  → поле «Video Url» (фрагмент 3–10 сек)
  → «Element 1» = портрет Бороды
  → промпт с @Video1 и @Element1

Конфиг сцен: data/pension/video/scenes_4.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "data" / "pension" / "video"
CONFIG_PATH = VIDEO_DIR / "scenes_4.json"
REF_PORTRAIT = VIDEO_DIR / "iosif_boroda_ref.png"
SOURCE_DIR = VIDEO_DIR / "source"

EDIT_MODEL = "fal-ai/kling-video/o3/pro/video-to-video/edit"

PROMPT_PREFIX = (
    "Preserve motion and timing from @Video1. Convert to 2D minimalist cartoon, "
    "simple black line art on solid white background. Main character as @Element1 "
    "(thick ginger beard, olive green PENS cap, black t-shirt). "
)


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def _run(cmd: list[str]) -> None:
    print("  $", " ".join(str(c) for c in cmd[:10]), ("..." if len(cmd) > 10 else ""))
    subprocess.run(cmd, check=True)


def _upload(path: Path) -> str:
    import fal_client

    url = fal_client.upload_file(str(path))
    print(f"  uploaded {path.name} → {url[:70]}...")
    return url


def _split_segment(src: Path, start: float, duration: float, dest: Path) -> None:
    """Вырезать фрагмент; Kling edit принимает 3–10 сек."""
    duration = min(max(duration, 3.0), 10.0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            _ffmpeg(),
            "-y",
            "-ss",
            str(start),
            "-i",
            str(src),
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ]
    )


def _kling_edit(
    *,
    prompt: str,
    video_url: str,
    element_url: str,
    style_url: str | None,
) -> dict:
    import fal_client

    full_prompt = PROMPT_PREFIX + prompt
    args: dict = {
        "prompt": full_prompt,
        "video_url": video_url,
        "keep_audio": False,
        "elements": [
            {
                "frontal_image_url": element_url,
                "reference_image_urls": [element_url],
            }
        ],
    }
    if style_url:
        args["image_urls"] = [style_url]

    print(f"  kling edit …")
    return fal_client.subscribe(EDIT_MODEL, arguments=args, with_logs=True)


async def _download(client: httpx.AsyncClient, url: str, dest: Path) -> None:
    r = await client.get(url, timeout=300.0)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"  saved {dest.name} ({len(r.content) // 1024} KB)")


def _concat(clips: list[Path], out: Path, fade_out: float = 1.0) -> None:
    # reuse from sibling script
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_pension_demo_video import _concat_clips

    _concat_clips(clips, out, fade_out=fade_out)


def _postprocess_scene(scene: dict, raw: Path, out: Path, overlays_dir: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_pension_demo_video import (
        _make_monitor_text_png,
        _overlay_monitor_text,
        _overlay_signs,
    )

    overlays_dir.mkdir(parents=True, exist_ok=True)
    if scene.get("sign_overlays"):
        tuples = [tuple(x) for x in scene["sign_overlays"]]
        _overlay_signs(raw, tuples, out, overlays_dir)
    elif scene.get("monitor_text_at_sec") is not None:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        text = cfg.get("monitor_text", "НА ПЕНСИЮ НИКОГДА!")
        _overlay_monitor_text(raw, text, float(scene["monitor_text_at_sec"]), out, overlays_dir)
    else:
        out.write_bytes(raw.read_bytes())


async def main() -> int:
    parser = argparse.ArgumentParser(description="4 сцены pension через Kling v2v edit")
    parser.add_argument(
        "--source",
        type=Path,
        help="исходное видео (по умолчанию из scenes_4.json или pension_demo_final.mp4)",
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--only", metavar="ID", help="одна сцена, напр. 01_laptop")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--split-only", action="store_true", help="только нарезка, без fal")
    parser.add_argument("--concat-only", action="store_true")
    parser.add_argument(
        "--confirm-spend",
        action="store_true",
        help="явное разрешение на платные вызовы fal/Kling (~$0.84/сек edit)",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    needs_fal = not args.split_only and not args.concat_only
    if needs_fal and not args.confirm_spend:
        print(
            "Платные вызовы fal отключены. Добавьте --confirm-spend, если сознательно хотите тратить кредиты.\n"
            "Бесплатно: --split-only, --concat-only",
            file=sys.stderr,
        )
        return 1
    if not (os.getenv("FAL_KEY") or "").strip() and needs_fal:
        print("FAL_KEY не задан в .env", file=sys.stderr)
        return 1

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    scenes = cfg["scenes"]
    if args.only:
        scenes = [s for s in scenes if s["id"] == args.only]
        if not scenes:
            print(f"Неизвестная сцена: {args.only}", file=sys.stderr)
            return 1

    segments_dir = VIDEO_DIR / "segments"
    clips_dir = VIDEO_DIR / "clips_v2"
    clips_final_dir = VIDEO_DIR / "clips_v2_final"
    segments_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)
    clips_final_dir.mkdir(parents=True, exist_ok=True)

    if args.concat_only:
        clips = [clips_final_dir / f"{s['id']}.mp4" for s in cfg["scenes"]]
        missing = [c for c in clips if not c.is_file()]
        if missing:
            print("Нет клипов:", ", ".join(p.name for p in missing), file=sys.stderr)
            return 1
        out = VIDEO_DIR / "pension_4scenes_final.mp4"
        _concat(clips, out)
        print(f"FINAL → {out}")
        return 0

    src = args.source
    if not src:
        name = cfg.get("source_video", "pension_demo_final.mp4")
        for candidate in (VIDEO_DIR / name, SOURCE_DIR / name, VIDEO_DIR / "pension_demo_final.mp4"):
            if candidate.is_file():
                src = candidate
                break
    if not src or not src.is_file():
        print(
            "Положите исходное видео в:\n"
            f"  {SOURCE_DIR}/\n"
            f"  или {VIDEO_DIR}/pension_demo_final.mp4\n"
            "и запустите снова, либо: --source path/to/video.mp4",
            file=sys.stderr,
        )
        return 1

    print(f"Source: {src}")

    for scene in scenes:
        sid = scene["id"]
        seg = segments_dir / f"{sid}.mp4"
        if not seg.is_file() or args.force:
            print(f"\n=== split {sid} ===")
            _split_segment(src, float(scene["start_sec"]), float(scene["duration_sec"]), seg)
        else:
            print(f"skip split {sid}")

    if args.split_only:
        print(f"\nСегменты → {segments_dir}")
        return 0

    if not REF_PORTRAIT.is_file():
        print(f"Нет референса персонажа: {REF_PORTRAIT}", file=sys.stderr)
        return 1

    style_name = cfg.get("style_image", "iosif_boroda_ref.png")
    style_path = VIDEO_DIR / style_name
    element_url = _upload(REF_PORTRAIT)
    style_url = _upload(style_path) if style_path.is_file() else None

    final_clips: list[Path] = []

    async with httpx.AsyncClient() as client:
        for scene in scenes:
            sid = scene["id"]
            seg = segments_dir / f"{sid}.mp4"
            clip_raw = clips_dir / f"{sid}.mp4"
            clip_out = clips_final_dir / f"{sid}.mp4"

            if clip_out.is_file() and clip_out.stat().st_size > 30000 and not args.force:
                print(f"skip edit {sid}")
                final_clips.append(clip_out)
                continue

            print(f"\n=== edit {sid} ===")
            video_url = _upload(seg)
            try:
                result = _kling_edit(
                    prompt=scene["prompt"],
                    video_url=video_url,
                    element_url=element_url,
                    style_url=style_url,
                )
            except Exception as exc:
                print(f"  FAIL {sid}: {exc}")
                continue

            out_url = (result.get("video") or {}).get("url")
            if not out_url:
                print(f"  FAIL {sid}: no video url")
                continue

            await _download(client, out_url, clip_raw)
            _postprocess_scene(scene, clip_raw, clip_out, VIDEO_DIR / "overlays_v2")
            final_clips.append(clip_out)
            print(f"  done → {clip_out}")

        if len(final_clips) == len(scenes) and not args.only:
            out = VIDEO_DIR / "pension_4scenes_final.mp4"
            print(f"\n=== concat {len(final_clips)} ===")
            _concat(final_clips, out)
            print(f"FINAL → {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
