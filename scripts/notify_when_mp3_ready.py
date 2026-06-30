#!/usr/bin/env python3
"""Wait for MP3 synthesis, send file(s) to Telegram, cleanup temp files."""
from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.empire_notify import send, send_file  # noqa: E402

TG_MAX_BYTES = 47 * 1024 * 1024


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


def wait_for_pid(pid: int, poll_sec: int = 20) -> None:
    while True:
        r = subprocess.run(["ps", "-p", str(pid)], capture_output=True)
        if r.returncode != 0:
            return
        time.sleep(poll_sec)


def cleanup(output: Path) -> None:
    parent = output.parent
    stem = output.stem
    for d in (parent / f".{stem}_chunks", parent / f".{stem}_preflight"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    for f in (parent / f".{stem}.log", parent / f".{stem}_tts.log"):
        f.unlink(missing_ok=True)


def split_for_telegram(mp3: Path, tmp_dir: Path) -> list[Path]:
    size = mp3.stat().st_size
    if size <= TG_MAX_BYTES:
        return [mp3]
    parts = math.ceil(size / TG_MAX_BYTES)
    dur = chunk_duration(mp3)
    if dur <= 0:
        raise RuntimeError("cannot read mp3 duration")
    seg_sec = dur / parts
    pattern = str(tmp_dir / f"{mp3.stem}_part%02d.mp3")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(mp3),
            "-f",
            "segment",
            "-segment_time",
            str(seg_sec),
            "-c",
            "copy",
            pattern,
        ],
        check=True,
        capture_output=True,
    )
    out = sorted(tmp_dir.glob(f"{mp3.stem}_part*.mp3"))
    if not out:
        raise RuntimeError("ffmpeg split produced no files")
    return out


def deliver_to_telegram(mp3: Path, label: str) -> bool:
    dur_min = chunk_duration(mp3) / 60
    size_mb = mp3.stat().st_size / (1024 * 1024)
    send(
        f"✅ Озвучка готова: {label}\n"
        f"Длительность: {dur_min:.0f} мин · {size_mb:.0f} МБ\n"
        f"Сейчас пришлю файлом в этот чат…"
    )
    with tempfile.TemporaryDirectory(prefix="tg_mp3_") as tmp:
        parts = split_for_telegram(mp3, Path(tmp))
        total = len(parts)
        for i, part in enumerate(parts, start=1):
            cap = label if total == 1 else f"{label} — часть {i}/{total}"
            if not send_file(part, caption=cap, as_audio=True):
                send(f"❌ Не удалось отправить часть {i}/{total} в Telegram.")
                return False
            time.sleep(1.5)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pid", type=int, default=0)
    parser.add_argument("--label", default="аудиокнига")
    args = parser.parse_args()

    if args.pid:
        wait_for_pid(args.pid)

    deadline = time.time() + 7200
    while time.time() < deadline:
        if args.output.is_file() and args.output.stat().st_size > 1_000_000:
            break
        time.sleep(15)
    else:
        send(f"❌ Озвучка «{args.label}»: таймаут, MP3 не появился.")
        return 1

    if not deliver_to_telegram(args.output, args.label):
        return 2

    cleanup(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
