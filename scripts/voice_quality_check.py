#!/usr/bin/env python3
"""
Compare Whisper quality on one audio file (audio vs model vs settings).

Usage:
  ./venv/bin/python scripts/voice_quality_check.py path/to/recording.mp3
  ./venv/bin/python scripts/voice_quality_check.py --models small,medium path/to/rec.mp3
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from voice_whisper import audio_probe, transcribe, whisper_settings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", type=Path)
    ap.add_argument(
        "--models",
        default="small,medium",
        help="comma-separated model sizes to compare",
    )
    ap.add_argument("--device", default=None)
    args = ap.parse_args()

    audio = args.audio
    if not audio.is_file():
        print(f"Not found: {audio}", file=sys.stderr)
        return 1

    cfg = whisper_settings()
    device = args.device or str(cfg["device"])
    probe = audio_probe(audio)

    print(f"File: {audio}")
    print(f"Size: {audio.stat().st_size // 1024} KiB")
    if probe:
        dur = float(probe.get("duration", "0") or 0)
        br = int(probe.get("bit_rate", "0") or 0)
        print(
            f"Codec: {probe.get('codec_name', '?')} | "
            f"{probe.get('sample_rate', '?')} Hz | "
            f"{probe.get('channels', '?')} ch | "
            f"{br // 1000} kbps | {dur:.1f}s"
        )
        if br and br < 48000:
            print("WARN: bitrate < 48 kbps — phone/recorder quality may be the bottleneck.")
        if dur > 600:
            print("WARN: >10 min — consider shorter clips for dictation.")
    else:
        print("ffprobe not available — install ffmpeg for audio diagnostics.")

    print(f"Settings: device={device} preprocess={cfg['preprocess']}")
    print("-" * 60)

    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        print(f"\n### model={model}")
        t0 = time.perf_counter()
        try:
            text = transcribe(audio, model_size=model, device=device)
        except Exception as e:
            print(f"FAIL: {e}", file=sys.stderr)
            continue
        elapsed = time.perf_counter() - t0
        preview = text[:800] + ("…" if len(text) > 800 else "")
        print(f"Time: {elapsed:.1f}s | chars: {len(text)}")
        print(preview)

    print("\n---")
    print("If medium is clearly better → set VOICE_WHISPER_MODEL=medium in /etc/empire/voice.env")
    print("If both are bad but audio bitrate is low → raise recorder quality on phone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
