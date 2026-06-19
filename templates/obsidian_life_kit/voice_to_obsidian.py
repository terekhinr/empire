#!/usr/bin/env python3
"""
Watch Life/voice/raw/ → faster-whisper → Life/inbox/*.md

Windows example:
  python scripts/voice_to_obsidian.py --once
  python scripts/voice_to_obsidian.py

Env:
  OBSIDIAN_VAULT  default F:\\YandexDisk\\obsidian (2)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

AUDIO_EXT = {".m4a", ".mp3", ".wav", ".ogg", ".webm", ".aac", ".flac"}


def default_vault() -> Path:
    return Path(os.environ.get("OBSIDIAN_VAULT", r"F:\YandexDisk\obsidian (2)"))


def paths(vault: Path) -> tuple[Path, Path, Path, Path]:
    life = vault / "Life"
    raw = life / "voice" / "raw"
    transcribed = life / "voice" / "transcribed"
    inbox = life / "inbox"
    processed = life / "voice" / "processed"
    for p in (raw, transcribed, inbox, processed):
        p.mkdir(parents=True, exist_ok=True)
    return raw, transcribed, inbox, processed


def slug_from_name(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[^\w\-]+", "-", stem).strip("-")
    return stem or "voice"


def transcribe(audio: Path, model_size: str, device: str) -> str:
    from faster_whisper import WhisperModel

    compute_type = "int8" if device == "cpu" else "float16"
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(
        str(audio),
        language="ru",
        vad_filter=True,
    )
    return "\n".join(s.text.strip() for s in segments if s.text.strip())


def write_note(
    inbox: Path,
    audio_rel: str,
    text: str,
    stamp: datetime,
) -> Path:
    fname = f"{stamp.strftime('%Y-%m-%d-%H%M')}-voice.md"
    out = inbox / fname
    body = f"""---
date: {stamp.strftime("%Y-%m-%d")}
source: voice
audio: "[[{audio_rel}]]"
tags: [inbox/voice]
---

## Транскрипт

{text}

## Действия

- [ ]
"""
    out.write_text(body, encoding="utf-8")
    return out


def process_file(
    audio: Path,
    vault: Path,
    raw: Path,
    transcribed: Path,
    inbox: Path,
    processed: Path,
    model_size: str,
    device: str,
) -> None:
    print(f"Transcribing: {audio.name} …")
    text = transcribe(audio, model_size, device)
    stamp = datetime.now()
    dest_audio = transcribed / audio.name
    if dest_audio.exists():
        dest_audio = transcribed / f"{stamp.strftime('%H%M%S')}-{audio.name}"
    audio.rename(dest_audio)
    rel = os.path.relpath(dest_audio, vault).replace("\\", "/")
    note = write_note(inbox, rel, text, stamp)
    marker = processed / f"{audio.stem}.done"
    marker.write_text(str(note), encoding="utf-8")
    print(f"  -> {note.name} ({len(text)} chars)")


def collect_pending(raw: Path, processed: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(raw.iterdir()):
        if not p.is_file() or p.suffix.lower() not in AUDIO_EXT:
            continue
        if (processed / f"{p.stem}.done").exists():
            continue
        out.append(p)
    return out


def run_watch(
    vault: Path,
    model_size: str,
    device: str,
    poll_sec: float,
) -> None:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    raw, transcribed, inbox, processed = paths(vault)

    class Handler(FileSystemEventHandler):
        def on_created(self, event):  # noqa: N802
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix.lower() in AUDIO_EXT:
                time.sleep(1.5)
                if path.is_file():
                    try:
                        process_file(
                            path, vault, raw, transcribed, inbox, processed,
                            model_size, device,
                        )
                    except Exception as e:
                        print(f"ERROR {path.name}: {e}", file=sys.stderr)

    for f in collect_pending(raw, processed):
        process_file(f, vault, raw, transcribed, inbox, processed, model_size, device)

    observer = Observer()
    observer.schedule(Handler(), str(raw), recursive=False)
    observer.start()
    print(f"Watching {raw} (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(poll_sec)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", type=Path, default=None)
    ap.add_argument("--model", default="small", help="tiny|base|small|medium")
    ap.add_argument("--device", default="auto", help="auto|cuda|cpu")
    ap.add_argument("--once", action="store_true", help="Process pending files and exit")
    ap.add_argument("--poll", type=float, default=2.0)
    args = ap.parse_args()

    vault = args.vault or default_vault()
    if not vault.is_dir():
        print(f"Vault not found: {vault}", file=sys.stderr)
        return 1

    device = args.device
    if device == "auto":
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
    print(f"Vault={vault} model={args.model} device={device}")

    raw, transcribed, inbox, processed = paths(vault)
    pending = collect_pending(raw, processed)
    if not pending:
        print(f"No new audio in {raw}")
        if args.once:
            return 0

    for f in pending:
        process_file(
            f, vault, raw, transcribed, inbox, processed, args.model, device,
        )

    if args.once:
        return 0

    run_watch(vault, args.model, device, args.poll)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
