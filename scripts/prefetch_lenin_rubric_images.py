#!/usr/bin/env python3
"""Скачать иллюстрации для рубрик канала Ленин."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rubric_posts import download_image, image_candidate_urls  # noqa: E402

DATA = ROOT / "data" / "lenin_rubrics.json"
MEDIA = ROOT / "media" / "lenin" / "rubrics"


async def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    MEDIA.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0
    for rubric, block in (data.get("rubrics") or {}).items():
        for entry in block.get("entries", []):
            eid = entry.get("id", "?")
            dest = MEDIA / f"{eid}.jpg"
            if dest.is_file() and dest.stat().st_size > 2048:
                print(f"skip {eid}")
                ok += 1
                continue
            done = False
            for url in image_candidate_urls(entry):
                try:
                    if await download_image(url, dest):
                        print(f"ok   {rubric}/{eid}")
                        ok += 1
                        done = True
                        break
                except Exception as exc:
                    print(f"err  {eid}: {exc}")
            if not done:
                print(f"FAIL {rubric}/{eid}")
                fail += 1
    fb = MEDIA / "_default_lenin.jpg"
    if not fb.is_file():
        u = "https://commons.wikimedia.org/wiki/Special:FilePath/Vladimir_Lenin.jpg?width=800"
        if await download_image(u, fb):
            print("ok   _default_lenin")
    print(f"\n{ok} ok, {fail} fail → {MEDIA}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
