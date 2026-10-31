#!/usr/bin/env python3
"""TXT → MP3 via Yandex SpeechKit TTS (native Russian `+` stress)."""
from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

LOGGER = logging.getLogger("yandex_tts")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VOICE = "filipp"
DEFAULT_SPEED = "0.95"
DEFAULT_LANG = "ru-RU"
MAX_CHUNK = 2500
RETRIES = 5
URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def api_key() -> str:
    load_env()
    key = (os.getenv("YANDEX_API_KEY") or os.getenv("SPEECHKIT_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("Нет YANDEX_API_KEY в .env")
    return key


def folder_id() -> str:
    load_env()
    return (os.getenv("YANDEX_FOLDER_ID") or os.getenv("YC_FOLDER_ID") or "").strip()


from tts_nsw import hard_slices_preserving_sil  # noqa: E402


def split_text(text: str, max_len: int = MAX_CHUNK) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paragraphs:
        cand = f"{buf}\n\n{para}".strip() if buf else para
        if len(cand) <= max_len:
            buf = cand
            continue
        if buf:
            chunks.append(buf)
            buf = ""
        if len(para) <= max_len:
            buf = para
            continue
        sentences = re.split(r"(?<=[.!?…])\s+", para)
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
                    chunks.extend(hard_slices_preserving_sil(sent, max_len))
                    buf = ""
        if buf:
            chunks.append(buf)
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def synth_chunk(
    text: str,
    *,
    voice: str,
    speed: str,
    out: Path,
) -> None:
    key = api_key()
    data = {
        "text": text,
        "lang": DEFAULT_LANG,
        "voice": voice,
        "format": "mp3",
        "speed": speed,
    }
    fid = folder_id()
    if fid:
        data["folderId"] = fid
    last_err = ""
    for attempt in range(1, RETRIES + 1):
        try:
            r = httpx.post(
                URL,
                headers={"Authorization": f"Api-Key {key}"},
                data=data,
                timeout=120.0,
            )
            if r.status_code == 200 and len(r.content) > 500:
                out.write_bytes(r.content)
                return
            last_err = f"{r.status_code} {r.text[:200]}"
            # rate limit
            if r.status_code in (429, 500, 503):
                time.sleep(2 * attempt)
                continue
            time.sleep(1)
        except Exception as exc:
            last_err = str(exc)
            time.sleep(2 * attempt)
    raise RuntimeError(f"Yandex TTS failed: {last_err}")


def concat_mp3(parts: list[Path], output: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        list_path = Path(f.name)
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")
    tmp = output.with_suffix(".tmp.mp3")
    try:
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
                "-c",
                "copy",
                str(tmp),
            ],
            check=True,
            capture_output=True,
        )
        tmp.replace(output)
    finally:
        list_path.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)


def convert_file(
    input_path: Path,
    output_path: Path,
    *,
    voice: str = DEFAULT_VOICE,
    speed: str = DEFAULT_SPEED,
    max_chunk: int = MAX_CHUNK,
    resume: bool = True,
) -> Path:
    text = input_path.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError("Empty text")
    chunks = split_text(text, max_chunk)
    LOGGER.info("%s → %s chunks, voice=%s", input_path.name, len(chunks), voice)
    work = output_path.parent / f".{output_path.stem}_yandex_chunks"
    work.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    for i, chunk in enumerate(chunks, 1):
        mp3 = work / f"chunk_{i:04d}.mp3"
        if resume and mp3.is_file() and mp3.stat().st_size > 500:
            parts.append(mp3)
            continue
        # skip pure latin
        if not re.search(r"[А-Яа-яЁё]", chunk):
            LOGGER.warning("skip latin chunk %s", i)
            continue
        synth_chunk(chunk, voice=voice, speed=speed, out=mp3)
        parts.append(mp3)
        time.sleep(0.15)
    if not parts:
        raise RuntimeError("No audio chunks")
    concat_mp3(parts, output_path)
    LOGGER.info("Wrote %s (%s bytes)", output_path, output_path.stat().st_size)
    return output_path


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="TXT → MP3 (Yandex SpeechKit)")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument("--voice", default=DEFAULT_VOICE)
    p.add_argument("--speed", default=DEFAULT_SPEED)
    p.add_argument("--max-chunk", type=int, default=MAX_CHUNK)
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()
    try:
        convert_file(
            args.input,
            args.output,
            voice=args.voice,
            speed=args.speed,
            max_chunk=args.max_chunk,
            resume=args.resume,
        )
        return 0
    except Exception:
        LOGGER.exception("fatal")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
