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
    ensure_classic_image,
    classic_image_abs_path,
    _CLASSIC_MEDIA_DIR,
)


async def main() -> int:
    data = json.loads(_CLASSIC_PATH.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    _CLASSIC_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0
    for entry in entries:
        eid = entry.get("id", "?")
        dest = classic_image_abs_path(entry)
        if dest.is_file() and dest.stat().st_size > 2048:
            print(f"skip {eid} (exists)")
            ok += 1
            continue
        rel = await ensure_classic_image(entry)
        if rel and dest.is_file():
            print(f"ok   {eid}")
            ok += 1
        else:
            print(f"FAIL {eid} ({entry.get('author')})")
            fail += 1
    print(f"\nDone: {ok} ok, {fail} failed, dir={_CLASSIC_MEDIA_DIR}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
