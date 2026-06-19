#!/usr/bin/env python3
"""
VPS: new audio in VOICE_INCOMING -> faster-whisper -> routed Obsidian notes.

Env:
  VOICE_INCOMING      default data/voice_incoming
  VAULT_STAGING       default data/voice_vault_staging  (mirror vault paths)
  VOICE_STATE_JSON    default data/voice_pipeline_state.json
  VOICE_ROUTE_CONFIG  default data/voice_route_config.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from voice_route import classify, load_config, write_voice_note

AUDIO_EXT = {".m4a", ".mp3", ".wav", ".ogg", ".webm", ".aac", ".flac"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def file_key(path: Path) -> str:
    stat = path.stat()
    return f"{path.name}:{stat.st_size}:{int(stat.st_mtime)}"


def load_state(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("done", []))


def save_state(path: Path, done: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"done": sorted(done)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def transcribe(audio: Path, model_size: str, device: str) -> str:
    from faster_whisper import WhisperModel

    compute_type = "int8" if device == "cpu" else "float16"
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _ = model.transcribe(str(audio), language="ru", vad_filter=True)
    return "\n".join(s.text.strip() for s in segments if s.text.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.environ.get("VOICE_WHISPER_MODEL", "small"))
    ap.add_argument("--device", default=os.environ.get("VOICE_WHISPER_DEVICE", "cpu"))
    args = ap.parse_args()

    root = repo_root()
    incoming = Path(os.environ.get("VOICE_INCOMING", root / "data/voice_incoming"))
    staging = Path(os.environ.get("VAULT_STAGING", root / "data/voice_vault_staging"))
    state_path = Path(os.environ.get("VOICE_STATE_JSON", root / "data/voice_pipeline_state.json"))

    config = load_config()
    audio_vault_path = config.get("audio_vault_path", "Life/voice/transcribed")
    transcribed = staging / audio_vault_path

    if not incoming.is_dir():
        print(f"No incoming dir: {incoming}", file=sys.stderr)
        return 1

    done = load_state(state_path)
    pending: list[Path] = []
    for p in sorted(incoming.iterdir()):
        if p.is_file() and p.suffix.lower() in AUDIO_EXT:
            key = file_key(p)
            if key not in done:
                pending.append(p)

    if not pending:
        print("No new audio.")
        return 0

    for audio in pending:
        key = file_key(audio)
        print(f"Transcribing: {audio.name}")
        try:
            text = transcribe(audio, args.model, args.device)
        except Exception as e:
            print(f"FAIL {audio.name}: {e}", file=sys.stderr)
            continue

        stamp = datetime.now()
        dest = transcribed / audio.name
        if dest.exists():
            dest = transcribed / f"{stamp.strftime('%H%M%S')}-{audio.name}"
        transcribed.mkdir(parents=True, exist_ok=True)
        audio.rename(dest)

        route = classify(audio.name, text, config)
        note_dir = staging / route.vault_path
        note = write_voice_note(
            note_dir,
            route=route,
            audio_name=dest.name,
            text=text,
            stamp=stamp,
            audio_vault_path=audio_vault_path,
        )
        done.add(key)
        save_state(state_path, done)
        print(f"  -> {route.vault_path}/{note.name} ({len(text)} chars, route={route.id})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
