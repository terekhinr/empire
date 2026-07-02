#!/usr/bin/env python3
"""Re-transcribe existing voice notes in staging (updates ## Транскрипт in place)."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from voice_route import load_config, strip_routing_prefix
from voice_whisper import audio_probe, transcribe

AUDIO_LINK_RE = re.compile(r'audio:\s*"\[\[[^\]]*/([^/\]]+)\]\]"')
TRANSCRIPT_RE = re.compile(
    r"(## Транскрипт\s*\n)(.*?)(\n## Действия)",
    re.DOTALL,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def staging_root() -> Path:
    import os

    return Path(os.environ.get("VAULT_STAGING", repo_root() / "data/voice_vault_staging"))


def audio_path_for_note(note: Path, audio_name: str, config: dict) -> Path | None:
    audio_vault = config.get("audio_vault_path", "Life/voice/transcribed")
    candidates = [
        staging_root() / audio_vault / audio_name,
        repo_root() / "data/voice_incoming" / audio_name,
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def iter_voice_notes(since: date | None) -> list[Path]:
    root = staging_root()
    notes: list[Path] = []
    for path in root.rglob("*-voice-*.md"):
        if since is not None:
            try:
                note_date = date.fromisoformat(path.name[:10])
            except ValueError:
                continue
            if note_date < since:
                continue
        notes.append(path)
    return sorted(notes)


def update_note(note: Path, new_text: str) -> bool:
    body = note.read_text(encoding="utf-8")
    m = TRANSCRIPT_RE.search(body)
    if not m:
        print(f"  SKIP no transcript block: {note.name}", file=sys.stderr)
        return False
    cleaned = strip_routing_prefix(new_text)
    updated = body[: m.start(2)] + cleaned + body[m.end(2) :]
    note.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-06-23", help="YYYY-MM-DD, reprocess notes from this date")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    since = date.fromisoformat(args.since) if args.since else None
    config = load_config()
    notes = iter_voice_notes(since)
    if args.limit:
        notes = notes[: args.limit]

    if not notes:
        print("No notes to reprocess.")
        return 0

    print(f"Re-transcribe {len(notes)} note(s) since {since}")
    ok = 0
    for note in notes:
        body = note.read_text(encoding="utf-8")
        link_m = AUDIO_LINK_RE.search(body)
        if not link_m:
            print(f"SKIP {note.relative_to(staging_root())}: no audio link")
            continue
        audio_name = link_m.group(1)
        audio = audio_path_for_note(note, audio_name, config)
        if not audio:
            print(f"SKIP {note.name}: audio missing ({audio_name})")
            continue

        probe = audio_probe(audio)
        dur = float(probe.get("duration", "0") or 0) if probe else 0
        print(f"\n{note.relative_to(staging_root())} <- {audio.name} ({dur:.0f}s)")
        if args.dry_run:
            ok += 1
            continue

        try:
            text = transcribe(audio)
        except Exception as e:
            print(f"  FAIL: {e}", file=sys.stderr)
            continue
        if update_note(note, text):
            print(f"  OK ({len(text)} chars)")
            ok += 1

    print(f"\nDone: {ok}/{len(notes)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
