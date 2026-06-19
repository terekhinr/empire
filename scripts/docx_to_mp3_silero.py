#!/usr/bin/env python3
"""DOCX/TXT -> MP3 via Silero TTS + RUAccent stress marks."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import torch
from docx import Document
from ruaccent import RUAccent

SPEAKER = "eugene"
SAMPLE_RATE = 48000
MAX_CHUNK = 1500
MIN_CHUNK_BYTES = 8000
RETRIES = 3


def load_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        doc = Document(str(path))
        paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paras)
    return path.read_text(encoding="utf-8").strip()


def split_text(text: str, max_len: int = MAX_CHUNK) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_len:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(para) <= max_len:
            current = para
            continue
        sentences = re.split(r"(?<=[.!?…])\s+", para)
        buf = ""
        for sent in sentences:
            if not sent:
                continue
            cand = f"{buf} {sent}".strip() if buf else sent
            if len(cand) <= max_len:
                buf = cand
            else:
                if buf:
                    chunks.append(buf)
                if len(sent) <= max_len:
                    buf = sent
                else:
                    for i in range(0, len(sent), max_len):
                        chunks.append(sent[i : i + max_len])
                    buf = ""
        if buf:
            current = buf
    if current:
        chunks.append(current)
    return chunks


def save_wav(path: Path, audio_tensor) -> None:
    samples = (audio_tensor.detach().cpu().numpy() * 32767).astype("int16")
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(samples.tobytes())


def chunk_ok(path: Path) -> bool:
    return path.is_file() and path.stat().st_size >= MIN_CHUNK_BYTES


def concat_wav_to_mp3(parts: list[Path], output: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        list_path = Path(f.name)
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")
    tmp_mp3 = output.with_suffix(".tmp.mp3")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(tmp_mp3),
        ],
        check=True,
        capture_output=True,
    )
    list_path.unlink(missing_ok=True)
    tmp_mp3.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="DOCX/TXT -> MP3 (Silero + RUAccent)")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--speaker", default=SPEAKER)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-chunks", action="store_true")
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Missing input: {args.input}", file=sys.stderr)
        return 1

    output = args.output or args.input.with_suffix(".mp3")
    text = load_text(args.input)
    chunks = split_text(text)
    if not chunks:
        print("Empty text", file=sys.stderr)
        return 1

    print(f"Input: {args.input}")
    print(f"Speaker: {args.speaker} | chunks: {len(chunks)} | chars: {len(text)}")

    out_dir = output.parent / f".{output.stem}_chunks"
    out_dir.mkdir(parents=True, exist_ok=True)
    stressed_dir = out_dir / "_stressed"
    stressed_dir.mkdir(exist_ok=True)

    print("Loading RUAccent (tiny)...", flush=True)
    accentizer = RUAccent()
    accentizer.load(omograph_model_size="turbo", use_dictionary=True, tiny_mode=True)
    for i, chunk in enumerate(chunks, start=1):
        stressed_path = stressed_dir / f"chunk_{i:04d}.txt"
        if not stressed_path.exists():
            stressed_path.write_text(accentizer.process_all(chunk), encoding="utf-8")
    del accentizer
    import gc
    gc.collect()

    print("Loading Silero v4_ru...", flush=True)
    model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language="ru",
        speaker="v4_ru",
        trust_repo=True,
    )
    model.to("cpu")

    parts: list[Path] = []
    failed: list[int] = []

    for i, chunk in enumerate(chunks, start=1):
        out = out_dir / f"chunk_{i:04d}.wav"
        if args.resume and chunk_ok(out):
            parts.append(out)
            print(f"[{i}/{len(chunks)}] skip {out.name}", flush=True)
            continue

        stressed = (stressed_dir / f"chunk_{i:04d}.txt").read_text(encoding="utf-8")
        ok = False
        for attempt in range(1, RETRIES + 1):
            try:
                audio = model.apply_tts(
                    text=stressed,
                    speaker=args.speaker,
                    sample_rate=SAMPLE_RATE,
                )
                save_wav(out, audio)
                if chunk_ok(out):
                    ok = True
                    break
                print(f"[{i}/{len(chunks)}] retry {attempt}: tiny file", flush=True)
            except Exception as exc:
                print(f"[{i}/{len(chunks)}] retry {attempt}: {exc}", flush=True)
                time.sleep(2 * attempt)
        if not ok:
            failed.append(i)
            print(f"[{i}/{len(chunks)}] FAILED", flush=True)
            continue
        parts.append(out)
        print(f"[{i}/{len(chunks)}] {out.name} ({len(chunk)} chars)", flush=True)

    if failed:
        print(f"Failed chunks: {failed}", file=sys.stderr)
        return 2

    if len(parts) != len(chunks):
        print(f"Chunk count mismatch: {len(parts)} != {len(chunks)}", file=sys.stderr)
        return 2

    print(f"Merging {len(parts)} wav -> {output}", flush=True)
    concat_wav_to_mp3(parts, output)

    if not args.keep_chunks:
        for p in parts:
            p.unlink(missing_ok=True)
        try:
            out_dir.rmdir()
        except OSError:
            pass

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Done: {output} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
