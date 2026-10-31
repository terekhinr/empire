#!/usr/bin/env python3
"""Скачать иллюстрации для рубрик канала Штерн."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rubric_posts import download_image, image_candidate_urls  # noqa: E402

DATA = ROOT / "data" / "stern_rubrics.json"
LEGACY = ROOT / "data" / "stern_athletic_legacy.json"
MEDIA = ROOT / "media" / "stern" / "rubrics"


async def _prefetch_entries(rubric: str, entries: list, ok: int, fail: int) -> tuple[int, int]:
    for entry in entries:
        eid = entry.get("id", "?")
        dest = MEDIA / f"{eid}.jpg"
        if dest.is_file() and dest.stat().st_size > 2048:
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
            except Exception:
                pass
        if not done:
            print(f"FAIL {rubric}/{eid}")
            fail += 1
    return ok, fail


async def main() -> int:
    MEDIA.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for rubric, block in (data.get("rubrics") or {}).items():
        ok, fail = await _prefetch_entries(rubric, block.get("entries", []), ok, fail)
    if LEGACY.is_file():
        legacy = json.loads(LEGACY.read_text(encoding="utf-8"))
        entries = (legacy.get("rubrics") or {}).get("athletic_legacy", {}).get("entries", [])
        ok, fail = await _prefetch_entries("athletic_legacy", entries, ok, fail)
    fb = MEDIA / "_default_stern.jpg"
    if not fb.is_file() or fb.stat().st_size < 2048:
        u = "https://commons.wikimedia.org/wiki/Special:FilePath/Kettlebell.jpg?width=800"
        if await download_image(u, fb):
            print("ok   _default_stern")
    print(f"\n{ok} ok, {fail} fail → {MEDIA}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
