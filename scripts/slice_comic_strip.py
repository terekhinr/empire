#!/usr/bin/env python3
"""Нарезка горизонтальной ленты комикса на кадры фаз (для анимации)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("pip install Pillow") from exc

ROOT = Path(__file__).resolve().parents[1]
PHASES_JSON = ROOT / "snegiri_kb" / "comic_phases_data.json"
COMICS = ROOT / "static" / "snegiri" / "assets" / "comics"


def slice_strip(strip_path: Path, out_dir: Path, panels: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    im = Image.open(strip_path)
    w, h = im.size
    panel_w = w // panels
    paths: list[Path] = []
    for i in range(panels):
        left = i * panel_w
        box = (left, 0, left + panel_w if i < panels - 1 else w, h)
        frame = im.crop(box)
        out = out_dir / f"{i + 1:02d}.webp"
        frame.save(out, "WEBP", quality=88, method=6)
        paths.append(out)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", action="append", help="swing, hand_switch (default: all in JSON)")
    args = parser.parse_args()

    data = json.loads(PHASES_JSON.read_text(encoding="utf-8"))
    slugs = args.slug or [k for k in data if not k.startswith("_")]

    for slug in slugs:
        spec = data.get(slug)
        if not spec:
            print(f"skip unknown slug: {slug}")
            continue
        panels = spec["panels"]
        frame_base = COMICS / "frames" / slug
        for perf in ("m", "f"):
            strip = COMICS / f"{slug}_{perf}.webp"
            if not strip.exists():
                strip = COMICS / f"{slug}_{perf}.png"
            if not strip.exists():
                print(f"missing: {strip}")
                continue
            out = frame_base / perf
            paths = slice_strip(strip, out, panels)
            print(f"OK {slug}_{perf}: {len(paths)} frames → {out}")


if __name__ == "__main__":
    main()
