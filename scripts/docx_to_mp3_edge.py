#!/usr/bin/env python3
"""DOCX/TXT -> MP3 via edge-tts with chunk verification and resume."""
from __future__ import annotations

import argparse
import asyncio
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts
from docx import Document

DEFAULT_VOICE = "ru-RU-DmitryNeural"
MAX_CHUNK = 1200
MIN_CHUNK_BYTES = 4000
MIN_DURATION_SEC = 0.8
RETRIES = 5
DEFAULT_WORKERS = 4

# If any of these appear in a Whisper transcript, SSML/markup leaked into audio.
BAD_TRANSCRIPT_PATTERNS = (
    re.compile(r"\bbreak\s*time\b", re.I),
    re.compile(r"\bspeak\b", re.I),
    re.compile(r"\bprosody\b", re.I),
    re.compile(r"\bxmlns\b", re.I),
    re.compile(r"\bvoice\s+name\b", re.I),
    re.compile(r"&lt;|&gt;|&amp;"),
    re.compile(r"меньше\s+time", re.I),
)


def normalize_for_tts(text: str) -> str:
    """Plain text only: edge-tts escapes <>& and reads SSML tags aloud."""
    text = re.sub(r"<\s*(\d)", r"меньше \1", text)
    text = re.sub(r">\s*(\d)", r"больше \1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def load_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        doc = Document(str(path))
        paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        raw = "\n\n".join(paras)
    else:
        raw = path.read_text(encoding="utf-8").strip()
    return normalize_for_tts(raw)


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
    communicate = edge_tts.Communicate(chunk, voice, rate=rate)
    await communicate.save(str(out))


def transcribe_mp3(path: Path) -> str:
    from faster_whisper import WhisperModel

    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(path), language="ru", vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()


def preflight_samples(chunks: list[str]) -> list[tuple[str, str]]:
    """Pick intro, comparison/table, and a middle chunk."""
    picks: list[tuple[str, str]] = [("intro", chunks[0][:500])]
    for i, chunk in enumerate(chunks):
        if "меньше 102" in chunk:
            picks.append(("comparison", chunk[:500]))
            break
    mid = chunks[len(chunks) // 2][:500]
    picks.append(("middle", mid))
    return picks


async def run_preflight(
    chunks: list[str],
    voice: str,
    rate: str,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for label, sample in preflight_samples(chunks):
        mp3 = out_dir / f"preflight_{label}.mp3"
        print(f"Preflight [{label}] synth...", flush=True)
        await synth_one(sample, voice, rate, mp3)
        if not chunk_ok(mp3):
            raise RuntimeError(f"Preflight [{label}]: bad audio file")
        transcript = transcribe_mp3(mp3)
        print(f"Preflight [{label}] transcript: {transcript[:160]}...", flush=True)
        for pat in BAD_TRANSCRIPT_PATTERNS:
            if pat.search(transcript):
                raise RuntimeError(
                    f"Preflight [{label}] failed: transcript contains {pat.pattern!r}"
                )
        if len(transcript) < 20:
            raise RuntimeError(f"Preflight [{label}] failed: transcript too short")
    print("Preflight OK — no SSML/markup artifacts detected.", flush=True)


async def synth_chunk_with_retries(
    index: int,
    total: int,
    chunk: str,
    voice: str,
    rate: str,
    out: Path,
) -> Path:
    ok = False
    for attempt in range(1, RETRIES + 1):
        try:
            await synth_one(chunk, voice, rate, out)
            if chunk_ok(out):
                ok = True
                break
            print(
                f"[{index}/{total}] retry {attempt}: "
                f"bad file size={out.stat().st_size if out.exists() else 0} "
                f"dur={chunk_duration(out):.2f}s",
                flush=True,
            )
        except Exception as exc:
            print(f"[{index}/{total}] retry {attempt}: {exc}", flush=True)
            await asyncio.sleep(2 * attempt)
    if not ok:
        raise RuntimeError(f"chunk {index} failed after {RETRIES} attempts")
    print(f"[{index}/{total}] {out.name} ({len(chunk)} chars)", flush=True)
    return out


async def synth_chunks(
    chunks: list[str],
    voice: str,
    rate: str,
    out_dir: Path,
    resume: bool,
    workers: int,
) -> tuple[list[Path], list[int]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(max(1, workers))
    failed: list[int] = []
    parts: list[Path | None] = [None] * len(chunks)

    async def worker(i: int, chunk: str) -> None:
        out = out_dir / f"chunk_{i:04d}.mp3"
        if resume and chunk_ok(out):
            parts[i - 1] = out
            print(f"[{i}/{len(chunks)}] skip {out.name}", flush=True)
            return
        async with sem:
            try:
                parts[i - 1] = await synth_chunk_with_retries(
                    i, len(chunks), chunk, voice, rate, out
                )
            except RuntimeError:
                failed.append(i)

    await asyncio.gather(*(worker(i, chunk) for i, chunk in enumerate(chunks, start=1)))
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
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
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

    print(f"Voice: {args.voice} | rate: {args.rate} | workers: {args.workers}")
    print(f"Input: {args.input} | chunks: {len(chunks)} | chars: {len(text)}")

    out_dir = output.parent / f".{output.stem}_chunks"
    preflight_dir = output.parent / f".{output.stem}_preflight"

    if not args.skip_preflight:
        asyncio.run(run_preflight(chunks, args.voice, args.rate, preflight_dir))
    if args.preflight_only:
        return 0

    parts, failed = asyncio.run(
        synth_chunks(chunks, args.voice, args.rate, out_dir, args.resume, args.workers)
    )
    if failed:
        print(f"Failed chunks: {failed}", file=sys.stderr)
        return 2
    if len(parts) != len(chunks) or any(p is None for p in parts):
        print(f"Chunk mismatch: incomplete synthesis", file=sys.stderr)
        return 2

    print(f"Merging {len(parts)} parts -> {output}", flush=True)
    concat_mp3(parts, output)  # type: ignore[arg-type]

    if not args.keep_chunks:
        for p in parts:
            p.unlink(missing_ok=True)
        for d in (out_dir, preflight_dir):
            try:
                d.rmdir()
            except OSError:
                pass
        log_path = output.parent / f".{output.stem}.log"
        log_path.unlink(missing_ok=True)

    dur = chunk_duration(output)
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"Done: {output} ({size_mb:.1f} MB, {dur/60:.1f} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
