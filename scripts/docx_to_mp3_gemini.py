#!/usr/bin/env python3
"""DOCX/TXT -> MP3 via Gemini TTS (expressive Russian narration)."""
from __future__ import annotations

import argparse
import base64
import os
import re
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

from docx import Document
from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = "charon"
MAX_CHUNK = 2500
MIN_CHUNK_BYTES = 5000
RETRIES = 3
PROMPT_PREFIX = (
    "Прочитай вслух по-русски как профессиональный диктор аудиокниги. "
    "Естественные интонации, правильные ударения, спокойный уверенный темп. "
    "Текст:\n\n"
)


def load_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


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


def pcm_to_wav(pcm: bytes, path: Path, sample_rate: int = 24000) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


def save_audio_blob(data: bytes, mime: str, path: Path) -> None:
    if mime in ("audio/L16", "audio/pcm", "audio/raw"):
        pcm_to_wav(data, path.with_suffix(".wav"))
        path.with_suffix(".wav").replace(path)
        return
    if mime in ("audio/wav", "audio/x-wav"):
        path.write_bytes(data)
        return
    if mime in ("audio/mpeg", "audio/mp3"):
        path.write_bytes(data)
        return
    # fallback: try wav header detection
    if data[:4] == b"RIFF":
        path.write_bytes(data)
        return
    pcm_to_wav(data, path)


def synth_chunk(
    client: genai.Client,
    model: str,
    voice: str,
    text: str,
) -> tuple[bytes, str]:
    resp = client.models.generate_content(
        model=model,
        contents=PROMPT_PREFIX + text,
        config=types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                language_code="ru-RU",
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                ),
            ),
        ),
    )
    part = resp.candidates[0].content.parts[0]
    raw = part.inline_data.data
    data = raw if isinstance(raw, (bytes, bytearray)) else base64.b64decode(raw)
    return data, part.inline_data.mime_type


def chunk_ok(path: Path) -> bool:
    return path.is_file() and path.stat().st_size >= MIN_CHUNK_BYTES


def concat_to_mp3(parts: list[Path], output: Path) -> None:
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
            "24000",
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
    parser = argparse.ArgumentParser(description="DOCX/TXT -> MP3 (Gemini TTS)")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-chunks", action="store_true")
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set", file=sys.stderr)
        return 1

    if not args.input.is_file():
        print(f"Missing input: {args.input}", file=sys.stderr)
        return 1

    output = args.output or args.input.with_suffix(".mp3")
    text = load_text(args.input)
    chunks = split_text(text)
    if not chunks:
        print("Empty text", file=sys.stderr)
        return 1

    print(f"Model: {args.model} | voice: {args.voice}")
    print(f"Input: {args.input} | chunks: {len(chunks)} | chars: {len(text)}")

    client = genai.Client(api_key=api_key)
    out_dir = output.parent / f".{output.stem}_chunks"
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    failed: list[int] = []

    for i, chunk in enumerate(chunks, start=1):
        out = out_dir / f"chunk_{i:04d}.wav"
        if args.resume and chunk_ok(out):
            parts.append(out)
            print(f"[{i}/{len(chunks)}] skip {out.name}", flush=True)
            continue

        ok = False
        for attempt in range(1, RETRIES + 1):
            try:
                data, mime = synth_chunk(client, args.model, args.voice, chunk)
                save_audio_blob(data, mime, out)
                if chunk_ok(out):
                    ok = True
                    break
                print(f"[{i}/{len(chunks)}] retry {attempt}: tiny ({mime})", flush=True)
            except Exception as exc:
                print(f"[{i}/{len(chunks)}] retry {attempt}: {exc}", flush=True)
                time.sleep(3 * attempt)
        if not ok:
            failed.append(i)
            print(f"[{i}/{len(chunks)}] FAILED", flush=True)
            continue
        parts.append(out)
        print(f"[{i}/{len(chunks)}] {out.name} ({len(chunk)} chars)", flush=True)
        time.sleep(0.5)

    if failed:
        print(f"Failed chunks: {failed}", file=sys.stderr)
        return 2
    if len(parts) != len(chunks):
        print(f"Chunk mismatch: {len(parts)} != {len(chunks)}", file=sys.stderr)
        return 2

    print(f"Merging {len(parts)} parts -> {output}", flush=True)
    concat_to_mp3(parts, output)

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
