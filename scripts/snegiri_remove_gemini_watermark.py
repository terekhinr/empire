#!/usr/bin/env python3
"""Точечное удаление watermark Gemini + восстановление перекрашенных зон."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "static" / "snegiri" / "assets"

# type: solid | clone
# box/from: доли (x1,y1,x2,y2)
FIXES: dict[str, list[dict]] = {
    "app-record.png": [
        {"type": "solid", "box": (0.70, 0.925, 1.0, 1.0), "color": (0, 0, 0)},
    ],
    "app-analyze.png": [
        {"type": "clone", "box": (0.44, 0.052, 0.56, 0.098), "from": (0.05, 0.12, 0.35, 0.22)},
    ],
    "app-result.png": [
        {"type": "clone", "box": (0.44, 0.038, 0.56, 0.088), "from": (0.05, 0.10, 0.35, 0.20)},
        {"type": "clone", "box": (0.47, 0.40, 0.53, 0.46), "from": (0.35, 0.32, 0.65, 0.40)},
    ],
    "hero-mockup-screen.png": [
        {"type": "clone", "box": (0.655, 0.835, 0.985, 0.945), "from": (0.335, 0.835, 0.655, 0.945)},
        {"type": "solid", "box": (0.66, 0.882, 0.985, 0.948), "color": (22, 22, 22)},
    ],
    "trainer-photo.png": [
        {"type": "clone", "box": (0.76, 0.875, 0.998, 0.998), "from": (0.04, 0.875, 0.24, 0.998)},
    ],
    "og-image.png": [
        {"type": "clone", "box": (0.70, 0.78, 0.94, 0.96), "from": (0.52, 0.78, 0.69, 0.96)},
    ],
    "track-01-spine.png": [
        {"type": "clone", "box": (0.82, 0.82, 0.998, 0.998), "from": (0.55, 0.82, 0.80, 0.998)},
    ],
    "track-02-kettlebell.png": [
        {"type": "clone", "box": (0.86, 0.86, 0.998, 0.998), "from": (0.68, 0.86, 0.85, 0.998)},
    ],
    "benefit-01-efficiency.png": [
        {"type": "clone", "box": (0.86, 0.86, 0.998, 0.998), "from": (0.68, 0.86, 0.85, 0.998)},
    ],
    "benefit-02-safety.png": [
        {"type": "clone", "box": (0.86, 0.86, 0.998, 0.998), "from": (0.68, 0.86, 0.85, 0.998)},
    ],
    "benefit-03-validation.png": [
        {"type": "clone", "box": (0.82, 0.86, 0.998, 0.998), "from": (0.62, 0.86, 0.80, 0.998)},
    ],
    "trainer-hero.png": [
        {"type": "clone", "box": (0.84, 0.88, 0.998, 0.998), "from": (0.62, 0.88, 0.82, 0.998)},
    ],
    "footer-bg.png": [
        {"type": "clone", "box": (0.84, 0.88, 0.998, 0.998), "from": (0.62, 0.88, 0.82, 0.998)},
    ],
}


def _box_px(w: int, h: int, box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    return (
        max(0, int(x1 * w)),
        max(0, int(y1 * h)),
        min(w, int(x2 * w)),
        min(h, int(y2 * h)),
    )


def _clone(arr: np.ndarray, box, from_box) -> None:
    h, w = arr.shape[:2]
    x1, y1, x2, y2 = _box_px(w, h, box)
    fx1, fy1, fx2, fy2 = _box_px(w, h, from_box)
    if x2 <= x1 or y2 <= y1 or fx2 <= fx1 or fy2 <= fy1:
        return
    src = arr[fy1:fy2, fx1:fx2]
    pw, ph = x2 - x1, y2 - y1
    pasted = np.array(Image.fromarray(src).resize((pw, ph), Image.Resampling.LANCZOS))
    arr[y1:y2, x1:x2] = pasted


def _solid(arr: np.ndarray, box, color: tuple[int, int, int] | None) -> None:
    h, w = arr.shape[:2]
    x1, y1, x2, y2 = _box_px(w, h, box)
    if color is None:
        color = tuple(np.median(arr[max(0, y1 - 8) : y1, x1:x2].reshape(-1, 3), axis=0).astype(int))
    arr[y1:y2, x1:x2] = color


def _draw_spine_icon(arr: np.ndarray, box) -> None:
    h, w = arr.shape[:2]
    x1, y1, x2, y2 = _box_px(w, h, box)
    patch = Image.fromarray(arr[y1:y2, x1:x2])
    draw = ImageDraw.Draw(patch)
    cx = (x2 - x1) // 2
    # простая белая «спина» вместо иконки Gemini
    pts = [(cx, 8), (cx - 18, 40), (cx - 10, 75), (cx, 95), (cx + 10, 75), (cx + 18, 40)]
    draw.line(pts, fill=(255, 255, 255), width=3, joint="curve")
    for px, py in pts[::2]:
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), outline=(255, 255, 255), width=2)
    arr[y1:y2, x1:x2] = np.array(patch)


def fix_file(path: Path, ops: list[dict]) -> None:
    im = Image.open(path).convert("RGB")
    arr = np.array(im)
    for op in ops:
        t = op["type"]
        if t == "clone":
            _clone(arr, op["box"], op["from"])
        elif t == "solid":
            _solid(arr, op["box"], op.get("color"))
        elif t == "draw_spine_icon":
            _draw_spine_icon(arr, op["box"])
    Image.fromarray(arr).save(path, optimize=True)


def main() -> None:
    for name, ops in FIXES.items():
        path = ASSETS / name
        if not path.exists():
            continue
        fix_file(path, ops)
        print(f"fixed: {name}")
    compress = ROOT / "scripts" / "snegiri_compress_assets.sh"
    if compress.exists():
        subprocess.run([str(compress)], check=True)


if __name__ == "__main__":
    main()
