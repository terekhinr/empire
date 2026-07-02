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
from voice_whisper import audio_probe, transcribe, whisper_settings

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


def main() -> int:
    ap = argparse.ArgumentParser()
    cfg = whisper_settings()
    ap.add_argument("--model", default=str(cfg["model"]))
    ap.add_argument("--device", default=str(cfg["device"]))
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
        probe = audio_probe(audio)
        if probe:
            print(
                f"Transcribing: {audio.name} "
                f"({probe.get('codec_name', '?')}, "
                f"{probe.get('sample_rate', '?')} Hz, "
                f"{probe.get('bit_rate', '?')} bps, "
                f"{float(probe.get('duration', '0') or 0):.0f}s)"
            )
        else:
            print(f"Transcribing: {audio.name}")
        try:
            text = transcribe(audio, model_size=args.model, device=args.device)
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
