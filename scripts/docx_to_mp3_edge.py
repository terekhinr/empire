#!/usr/bin/env python3
"""DOCX/TXT -> MP3 via edge-tts with chunk verification and resume."""
from __future__ import annotations

import argparse
import asyncio
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import edge_tts
from docx import Document

DEFAULT_VOICE = "ru-RU-DmitryNeural"
MAX_CHUNK = 1200
MIN_CHUNK_BYTES = 4000
MIN_DURATION_SEC = 0.8
RETRIES = 5


def load_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        doc = Document(str(path))
        paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paras)
    return path.read_text(encoding="utf-8").strip()


def to_ssml(text: str) -> str:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    body = '<break time="400ms"/>'.join(paras)
    return f"<speak>{body}</speak>"


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


def chunk_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def chunk_ok(path: Path) -> bool:
    return (
        path.is_file()
        and path.stat().st_size >= MIN_CHUNK_BYTES
        and chunk_duration(path) >= MIN_DURATION_SEC
    )


async def synth_one(chunk: str, voice: str, rate: str, out: Path) -> None:
    ssml = to_ssml(chunk)
    communicate = edge_tts.Communicate(ssml, voice, rate=rate)
    await communicate.save(str(out))


async def synth_chunks(
    chunks: list[str],
    voice: str,
    rate: str,
    out_dir: Path,
    resume: bool,
) -> tuple[list[Path], list[int]]:
    parts: list[Path] = []
    failed: list[int] = []
    for i, chunk in enumerate(chunks, start=1):
        out = out_dir / f"chunk_{i:04d}.mp3"
        if resume and chunk_ok(out):
            parts.append(out)
            print(f"[{i}/{len(chunks)}] skip {out.name}", flush=True)
            continue
        ok = False
        for attempt in range(1, RETRIES + 1):
            try:
                await synth_one(chunk, voice, rate, out)
                if chunk_ok(out):
                    ok = True
                    break
                print(
                    f"[{i}/{len(chunks)}] retry {attempt}: "
                    f"bad file size={out.stat().st_size if out.exists() else 0} "
                    f"dur={chunk_duration(out):.2f}s",
                    flush=True,
                )
            except Exception as exc:
                print(f"[{i}/{len(chunks)}] retry {attempt}: {exc}", flush=True)
                time.sleep(2 * attempt)
        if not ok:
            failed.append(i)
            print(f"[{i}/{len(chunks)}] FAILED", flush=True)
            continue
        parts.append(out)
        print(f"[{i}/{len(chunks)}] {out.name} ({len(chunk)} chars)", flush=True)
        await asyncio.sleep(0.3)
    return parts, failed


def concat_mp3(parts: list[Path], output: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        list_path = Path(f.name)
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")
    tmp = output.with_suffix(".tmp.mp3")
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
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(tmp),
        ],
        check=True,
        capture_output=True,
    )
    list_path.unlink(missing_ok=True)
    tmp.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="DOCX/TXT -> MP3 (edge-tts)")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--rate", default="-5%")
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

    print(f"Voice: {args.voice} | rate: {args.rate}")
    print(f"Input: {args.input} | chunks: {len(chunks)} | chars: {len(text)}")

    out_dir = output.parent / f".{output.stem}_chunks"
    out_dir.mkdir(parents=True, exist_ok=True)

    parts, failed = asyncio.run(
        synth_chunks(chunks, args.voice, args.rate, out_dir, args.resume)
    )
    if failed:
        print(f"Failed chunks: {failed}", file=sys.stderr)
        return 2
    if len(parts) != len(chunks):
        print(f"Chunk mismatch: {len(parts)} != {len(chunks)}", file=sys.stderr)
        return 2

    print(f"Merging {len(parts)} parts -> {output}", flush=True)
    concat_mp3(parts, output)

    if not args.keep_chunks:
        for p in parts:
            p.unlink(missing_ok=True)
        try:
            out_dir.rmdir()
        except OSError:
            pass

    dur = chunk_duration(output)
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Done: {output} ({size_mb:.1f} MB, {dur/60:.1f} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
