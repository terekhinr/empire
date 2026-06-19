#!/usr/bin/env python3
"""Подтянуть image: из vault к pending Obsidian-черновику (после sync с ПК)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: obsidian_refresh_draft_image.py <draft_id>", file=sys.stderr)
        return 1
    d_id = int(sys.argv[1])
    import obsidian_content as oc
    from main import PostDraft, async_session, generate_image
    from sqlalchemy import select

    async with async_session() as session:
        draft = await session.get(PostDraft, d_id)
        if not draft:
            print(f"No draft #{d_id}", file=sys.stderr)
            return 1
        img_f = await oc.resolve_image_for_topic_raw(
            draft.topic_raw, generate_image, d_id, draft.persona_key
        )
        if not img_f:
            eid = oc.parse_obsidian_entry_id(draft.topic_raw)
            entry = oc.queue_entry_by_id(eid) if eid else None
            print(f"Image not found. Expected: {(entry or {}).get('image')}", file=sys.stderr)
            return 1
        draft.image_path = img_f
        await session.commit()
        print(f"OK #{d_id} → {img_f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
