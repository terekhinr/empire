#!/usr/bin/env python3
"""Один пост из Obsidian queue → канал pension (текст + таблица-картинка)."""
from __future__ import annotations

import asyncio
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")

_TABLE_SEP = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")


def _body_without_markdown_table(body: str) -> str:
    lines = body.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if "|" in lines[i] and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


async def main() -> int:
    entry_id = sys.argv[1] if len(sys.argv) > 1 else "pension-kem-byt-2026-06-08"
    import obsidian_content as oc
    from main import (
        PostDraft,
        _send_draft_to_channel,
        async_session,
        finalize_public_post,
        fix_html_safety,
    )
    from tools.render_obsidian_table_png import parse_markdown_table, render_table_png

    entry = oc.queue_entry_by_id(entry_id)
    if not entry:
        print(f"Not in queue: {entry_id}", file=sys.stderr)
        return 1

    body = entry.get("body_markdown") or ""
    parsed = parse_markdown_table(body)
    img_path = None
    if parsed:
        title = ""
        m = re.search(r"^###\s+(.+)$", body, re.M)
        if m:
            title = m.group(1).strip()
        img_path = ROOT / "media" / "pension" / "obsidian" / f"{entry_id}-table.png"
        render_table_png(parsed[0], parsed[1], img_path, title=title)
        entry = dict(entry)
        entry["body_markdown"] = _body_without_markdown_table(body)

    text = oc.build_post_html(
        entry, fix_html_fn=fix_html_safety, finalize_fn=finalize_public_post
    )
    topic = oc.topic_raw_for_entry(entry)

    from aiogram.types import FSInputFile
    from main import bot, _platform_targets, _admin_caption_for_photo

    async with async_session() as session:
        draft = PostDraft(
            persona_key="pension",
            text_content=text,
            image_path=str(img_path) if img_path and img_path.is_file() else None,
            topic_raw=topic,
            decision="approved",
            status="draft",
        )
        session.add(draft)
        await session.commit()

        tg_id = _platform_targets().get("pension", {}).get("tg")
        if not tg_id:
            print("FAIL: no pension channel", file=sys.stderr)
            return 1

        ok, err = True, None
        try:
            if draft.image_path and Path(draft.image_path).is_file():
                if "<blockquote>" in text:
                    cut = text.index("<blockquote>")
                    caption, extra = text[:cut].rstrip(), text[cut:]
                else:
                    caption, extra = text, None
                if len(caption) > 1000:
                    caption, tail = _admin_caption_for_photo(caption, max_len=1000)
                    extra = (tail or "") + (extra or "")
                await bot.send_photo(
                    tg_id,
                    photo=FSInputFile(draft.image_path),
                    caption=caption,
                    parse_mode="HTML",
                )
                if extra:
                    await bot.send_message(tg_id, extra, parse_mode="HTML")
            else:
                ok, err, _msg_id = await _send_draft_to_channel(draft)
        except Exception as exc:
            ok, err = False, str(exc)
        if not ok:
            print("FAIL:", err, file=sys.stderr)
            return 1
        draft.status = "published"
        draft.decided_at = datetime.now(timezone.utc)
        await session.commit()
        print(f"OK #{draft.id} image={draft.image_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
