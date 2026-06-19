#!/usr/bin/env python3
"""Скачать все портреты для рубрики «Классическая баня» (gdepar)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gdepar_content import (  # noqa: E402
    _CLASSIC_PATH,
    _download_classic_image,
    _classic_image_candidate_urls,
    _CLASSIC_MEDIA_DIR,
)


async def main() -> int:
    data = json.loads(_CLASSIC_PATH.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    _CLASSIC_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0
    for entry in entries:
        eid = entry.get("id", "?")
        dest = _CLASSIC_MEDIA_DIR / f"{eid}.jpg"
        if dest.is_file() and dest.stat().st_size > 2048:
            print(f"skip {eid} (exists)")
            ok += 1
            continue
        done = False
        for url in _classic_image_candidate_urls(entry):
            try:
                if await _download_classic_image(url, dest):
                    print(f"ok   {eid} <- {url[:70]}...")
                    ok += 1
                    done = True
                    break
            except Exception as exc:
                print(f"err  {eid} {url[:50]}... {exc}")
        if not done:
            print(f"FAIL {eid}")
            fail += 1
    # общий fallback — русская баня
    fb = _CLASSIC_MEDIA_DIR / "_default_banya.jpg"
    if not fb.is_file():
        fb_urls = [
            "https://commons.wikimedia.org/wiki/Special:FilePath/Russian_banya_(Museum_of_wooden_architecture).jpg?width=800",
        ]
        for u in fb_urls:
            if await _download_classic_image(u, fb):
                print("ok   _default_banya")
                break
    print(f"\nDone: {ok} ok, {fail} failed, dir={_CLASSIC_MEDIA_DIR}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
