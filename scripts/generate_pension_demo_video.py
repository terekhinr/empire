#!/usr/bin/env python3
"""Ролик «На пенсию НИКОГДА» — ключевые кадры Flux + Kling O3 через fal.ai + монтаж."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "pension" / "video"
REF_PORTRAIT = OUT_DIR / "iosif_boroda_ref.png"

STYLE = (
    "2D cartoon illustration, bold black outlines on pure white background, "
    "minimal flat cel-shading, editorial animation, clean vector comic style. "
    "No photorealism, no gradients on background, white void room."
)

CHARACTER = (
    "Middle-aged man, thick ginger beard, olive green baseball cap with white text PENS, "
    "black crew-neck t-shirt — Iosif Boroda."
)

NEGATIVE = (
    "photorealistic, 3d render, photograph, blurry, watermark, text errors, "
    "colorful background, detailed textures, anime"
)

SCENES: list[dict] = [
    {
        "id": "01_room_wide",
        "duration": "6",
        "keyframe": (
            f"{STYLE} Wide shot small room. Window on the left with ficus plant on windowsill, "
            f"trees and clouds visible outside. Desk against right wall with open laptop. "
            f"{CHARACTER} sits on chair at desk, leaning forward furiously typing on laptop. "
            "Black line art only, white background."
        ),
        "motion": (
            f"{STYLE} Wide establishing shot of small room. Window left, ficus on sill, desk right. "
            "@Element1 sits at laptop and types intensely, shoulders tense, slight camera push-in."
        ),
        "mode": "ref",
    },
    {
        "id": "02_to_window",
        "duration": "4",
        "keyframe": (
            f"{STYLE} Medium shot. {CHARACTER} stands up from desk chair, alarmed expression, "
            "turning toward window on the left. Laptop on desk, white room black outlines."
        ),
        "motion": (
            f"{STYLE} @Element1 hears noise, stands up abruptly from chair and walks toward "
            "the left window with urgent steps."
        ),
        "mode": "ref",
    },
    {
        "id": "03_pov_demo",
        "duration": "6",
        "keyframe": (
            f"{STYLE} POV looking down from third floor window. Street below filled with cartoon "
            "protest crowd marching, people holding blank empty rectangular protest signs, "
            "no text on signs. Trees line the street, white sky black outlines."
        ),
        "motion": (
            f"{STYLE} First-person POV from third floor window looking down. Camera slowly pans "
            "across marching cartoon crowd holding blank protest signs, street demonstration below."
        ),
        "mode": "i2v",
        "overlays": [
            (1.0, 2.2, "На пенсию в 60!"),
            (2.2, 3.4, "На пенсию в 50 лет!"),
            (3.4, 4.6, "На пенсию в 30!"),
            (4.6, 5.8, "На пенсию в 0!"),
        ],
    },
    {
        "id": "04_close_window",
        "duration": "4",
        "keyframe": (
            f"{STYLE} {CHARACTER} at window slamming it shut with both hands, determined angry face. "
            "Ficus on sill, white room black line art."
        ),
        "motion": (
            f"{STYLE} @Element1 slams the window shut firmly, then turns and walks back toward "
            "the desk with laptop."
        ),
        "mode": "ref",
    },
    {
        "id": "05_monitor",
        "duration": "5",
        "keyframe": (
            f"{STYLE} Over-the-shoulder shot behind @Element1 ginger beard and PENS cap, "
            "looking at laptop screen showing blank white screen with cursor. Desk, white room."
        ),
        "motion": (
            f"{STYLE} Over-shoulder view of @Element1 at laptop. Camera moves closer to monitor, "
            "typing motion on keyboard."
        ),
        "mode": "ref",
        "monitor_text": "НА ПЕНСИЮ НИКОГДА!",
        "monitor_text_start": 2.5,
    },
]


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def _run(cmd: list[str]) -> None:
    print("  $", " ".join(cmd[:8]), ("..." if len(cmd) > 8 else ""))
    subprocess.run(cmd, check=True)


async def _flux_keyframe(
    client: httpx.AsyncClient,
    fal_key: str,
    slug: str,
    prompt: str,
    dest: Path,
    *,
    force: bool,
) -> bool:
    if dest.is_file() and dest.stat().st_size > 8000 and not force:
        print(f"  skip keyframe {slug}")
        return True
    payload = {
        "prompt": prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
        "negative_prompt": NEGATIVE,
    }
    res = await client.post(
        "https://fal.run/fal-ai/flux/dev",
        headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180.0,
    )
    if res.status_code != 200:
        print(f"  FAIL keyframe {slug}: {res.status_code} {res.text[:200]}")
        return False
    img_url = (res.json().get("images") or [{}])[0].get("url")
    if not img_url:
        print(f"  FAIL keyframe {slug}: no url")
        return False
    img = await client.get(img_url, timeout=120.0)
    img.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(img.content)
    print(f"  ok keyframe {slug} ({len(img.content) // 1024} KB)")
    return True


def _upload_fal(path: Path) -> str:
    import fal_client

    url = fal_client.upload_file(str(path))
    print(f"  uploaded {path.name} → {url[:60]}...")
    return url


def _kling_video(
    *,
    mode: str,
    motion: str,
    start_url: str,
    element_url: str | None,
    duration: str,
) -> dict:
    import fal_client

    if mode == "ref":
        args: dict = {
            "prompt": motion,
            "start_image_url": start_url,
            "duration": duration,
            "aspect_ratio": "16:9",
            "generate_audio": False,
        }
        if element_url:
            args["elements"] = [
                {
                    "frontal_image_url": element_url,
                    "reference_image_urls": [element_url],
                }
            ]
        model = "fal-ai/kling-video/o3/pro/reference-to-video"
    else:
        args = {
            "prompt": motion,
            "image_url": start_url,
            "duration": duration,
            "aspect_ratio": "16:9",
            "generate_audio": False,
        }
        model = "fal-ai/kling-video/o3/pro/image-to-video"

    print(f"  kling {model.split('/')[-1]} {duration}s …")
    return fal_client.subscribe(model, arguments=args, with_logs=True)


async def _download_video(client: httpx.AsyncClient, url: str, dest: Path) -> None:
    r = await client.get(url, timeout=300.0)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"  saved clip {dest.name} ({len(r.content) // 1024} KB)")


def _make_sign_png(text: str, path: Path, *, w: int = 640, h: int = 320) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    # poster board
    margin = 12
    draw.rounded_rectangle(
        (margin, margin, w - margin, h - margin),
        radius=8,
        fill=(255, 255, 255, 240),
        outline=(0, 0, 0, 255),
        width=4,
    )
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    lines = textwrap.wrap(text, width=16)
    line_h = 34
    total_h = len(lines) * line_h
    y0 = (h - total_h) // 2
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw) // 2, y0 + i * line_h), line, fill=(0, 0, 0, 255), font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def _make_monitor_text_png(text: str, path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    w, h = 960, 540
    img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, w - 40, h - 40), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=3)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((w - tw) // 2, (h - th) // 2), text, fill=(0, 0, 0, 255), font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def _overlay_signs(
    clip: Path,
    overlays: list[tuple[float, float, str]],
    out: Path,
    tmp_dir: Path,
) -> None:
    ff = _ffmpeg()
    pngs: list[Path] = []
    filters: list[str] = []
    for i, (t0, t1, text) in enumerate(overlays):
        png = tmp_dir / f"sign_{i}.png"
        _make_sign_png(text, png)
        pngs.append(png)
        inp = f"[{i + 1}:v]"
        out_label = f"[v{i}]" if i < len(overlays) - 1 else "[vout]"
        base = "[0:v]" if i == 0 else f"[v{i - 1}]"
        filters.append(
            f"{base}{inp}overlay=(W-w)/2:(H-h)/2:enable='between(t,{t0},{t1})'{out_label}"
        )
    filter_complex = ";".join(filters)
    cmd = [ff, "-y", "-i", str(clip)]
    for p in pngs:
        cmd += ["-i", str(p)]
    cmd += [
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(out),
    ]
    _run(cmd)


def _overlay_monitor_text(clip: Path, text: str, t_start: float, out: Path, tmp_dir: Path) -> None:
    ff = _ffmpeg()
    png = tmp_dir / "monitor_text.png"
    _make_monitor_text_png(text, png)
    _run(
        [
            ff,
            "-y",
            "-i",
            str(clip),
            "-i",
            str(png),
            "-filter_complex",
            f"[0:v][1:v]overlay=(W*0.25):(H*0.2):enable='gte(t,{t_start})'[vout]",
            "-map",
            "[vout]",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(out),
        ]
    )


def _concat_clips(clips: list[Path], out: Path, *, fade_out: float = 1.0) -> None:
    ff = _ffmpeg()
    list_file = out.parent / "concat_list.txt"
    lines = []
    for c in clips:
        lines.append(f"file '{c.resolve()}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp = out.parent / "_concat_tmp.mp4"
    _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(tmp)])
    # fade to black on last ~1s
    probe = subprocess.run(
        [ff, "-i", str(tmp), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    dur = 0.0
    for line in probe.stderr.splitlines():
        if "Duration:" in line:
            part = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = part.split(":")
            dur = float(h) * 3600 + float(m) * 60 + float(s)
            break
    fade_start = max(0.0, dur - fade_out)
    _run(
        [
            ff,
            "-y",
            "-i",
            str(tmp),
            "-vf",
            f"fade=t=out:st={fade_start}:d={fade_out}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(out),
        ]
    )
    tmp.unlink(missing_ok=True)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Генерация демо-ролика pension через fal.ai")
    parser.add_argument("--force", action="store_true", help="перегенерировать даже если файлы есть")
    parser.add_argument("--only", metavar="ID", help="только одна сцена, напр. 01_room_wide")
    parser.add_argument("--keyframes-only", action="store_true", help="только Flux keyframes")
    parser.add_argument("--concat-only", action="store_true", help="только склейка clips_final → final")
    parser.add_argument(
        "--confirm-spend",
        action="store_true",
        help="явное разрешение на платные вызовы fal/Flux/Kling",
    )
    args = parser.parse_args()

    if args.concat_only:
        cdir = OUT_DIR / "clips_final"
        clips = [cdir / f"{s['id']}.mp4" for s in SCENES]
        missing = [c for c in clips if not c.is_file()]
        if missing:
            print("Нет клипов:", ", ".join(p.name for p in missing), file=sys.stderr)
            return 1
        final_path = OUT_DIR / "pension_demo_final.mp4"
        print(f"=== concat {len(clips)} clips ===")
        _concat_clips(clips, final_path)
        print(f"FINAL → {final_path}")
        return 0

    load_dotenv(ROOT / ".env")
    if not args.confirm_spend:
        print(
            "Платные вызовы fal отключены. Добавьте --confirm-spend, если сознательно хотите тратить кредиты.\n"
            "Бесплатно: --concat-only",
            file=sys.stderr,
        )
        return 1
    fal_key = (os.getenv("FAL_KEY") or "").strip()
    if not fal_key:
        print("FAL_KEY не задан в .env", file=sys.stderr)
        return 1
    if not REF_PORTRAIT.is_file():
        print(f"Нет референса: {REF_PORTRAIT}", file=sys.stderr)
        return 1

    scenes = SCENES
    if args.only:
        scenes = [s for s in SCENES if s["id"] == args.only]
        if not scenes:
            print(f"Неизвестная сцена: {args.only}", file=sys.stderr)
            return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    keyframes_dir = OUT_DIR / "keyframes"
    clips_dir = OUT_DIR / "clips"
    clips_final_dir = OUT_DIR / "clips_final"
    overlays_dir = OUT_DIR / "overlays"
    keyframes_dir.mkdir(exist_ok=True)
    clips_dir.mkdir(exist_ok=True)
    clips_final_dir.mkdir(exist_ok=True)

    manifest: dict = {"scenes": [], "final": None}

    async with httpx.AsyncClient() as client:
        for scene in scenes:
            sid = scene["id"]
            print(f"\n=== {sid} ===")
            kf_path = keyframes_dir / f"{sid}.jpg"
            ok = await _flux_keyframe(
                client, fal_key, sid, scene["keyframe"], kf_path, force=args.force
            )
            manifest["scenes"].append({"id": sid, "keyframe": str(kf_path), "ok_keyframe": ok})
            if not ok:
                continue

        if args.keyframes_only or args.skip_video:
            (OUT_DIR / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"\nГотово (keyframes) → {OUT_DIR}")
            return 0

        element_url = _upload_fal(REF_PORTRAIT)
        final_clips: list[Path] = []

        for scene in scenes:
            sid = scene["id"]
            kf_path = keyframes_dir / f"{sid}.jpg"
            clip_raw = clips_dir / f"{sid}.mp4"
            clip_out = clips_final_dir / f"{sid}.mp4"

            if clip_out.is_file() and clip_out.stat().st_size > 50000 and not args.force:
                print(f"skip clip {sid}")
                final_clips.append(clip_out)
                continue

            if not kf_path.is_file():
                print(f"skip {sid}: no keyframe")
                continue

            start_url = _upload_fal(kf_path)
            try:
                result = _kling_video(
                    mode=scene["mode"],
                    motion=scene["motion"],
                    start_url=start_url,
                    element_url=element_url if scene["mode"] == "ref" else None,
                    duration=scene["duration"],
                )
            except Exception as exc:
                print(f"  FAIL kling {sid}: {exc}")
                continue

            video_url = (result.get("video") or {}).get("url")
            if not video_url:
                print(f"  FAIL kling {sid}: no video url in {result}")
                continue

            await _download_video(client, video_url, clip_raw)

            current = clip_raw
            if scene.get("overlays"):
                _overlay_signs(clip_raw, scene["overlays"], clip_out, overlays_dir)
                current = clip_out
            elif scene.get("monitor_text"):
                _overlay_monitor_text(
                    clip_raw,
                    scene["monitor_text"],
                    scene.get("monitor_text_start", 2.0),
                    clip_out,
                    overlays_dir,
                )
                current = clip_out
            else:
                clip_out.write_bytes(clip_raw.read_bytes())
                current = clip_out

            final_clips.append(current)
            print(f"  scene done → {current}")

        if len(final_clips) >= 1 and not args.only:
            final_path = OUT_DIR / "pension_demo_final.mp4"
            if final_path.is_file() and not args.force:
                print(f"\nfinal exists: {final_path}")
            else:
                print(f"\n=== concat {len(final_clips)} clips ===")
                _concat_clips(final_clips, final_path)
                print(f"FINAL → {final_path}")
            manifest["final"] = str(final_path)

    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
