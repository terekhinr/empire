#!/usr/bin/env python3
"""Нарезка YouTube-фрагментов для матрицы техники Снегирей.

Пример (пилот — мах, TGU, рывок):
  ./venv/bin/python tools/stern_technique_clip.py --pilot

Один клип:
  ./venv/bin/python tools/stern_technique_clip.py \\
      --url 'https://www.youtube.com/watch?v=92-xf--nx88' \\
      --start 0:00 --end 2:45 \\
      --out media/stern/technique_clips/sfg_swing_0-145.mp4

Матрица (все pending):
  ./venv/bin/python tools/stern_technique_clip.py --from-matrix --limit 5
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "data" / "stern_technique_matrix_161_200.json"
OUT_DIR = ROOT / "media" / "stern" / "technique_clips"
YTDLP = ROOT / "venv" / "bin" / "yt-dlp"


def _ffmpeg() -> str:
    for candidate in ("/usr/bin/ffmpeg", "ffmpeg"):
        try:
            subprocess.run([candidate, "-version"], capture_output=True, check=True)
            return candidate
        except Exception:
            continue
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def parse_ts(ts: str) -> float:
    """MM:SS или HH:MM:SS → секунды."""
    parts = [float(p) for p in ts.strip().split(":")]
    if len(parts) == 2:
        m, s = parts
        return m * 60 + s
    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    raise ValueError(f"bad timestamp: {ts!r}")


def slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", s.lower())
    return s.strip("_")[:48] or "clip"


def cut_clip(
    url: str,
    start: str,
    end: str,
    out: Path,
    *,
    reencode: bool = True,
) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = parse_ts(start)
    t1 = parse_ts(end)
    if t1 <= t0:
        raise ValueError(f"end {end} must be after start {start}")
    ff = _ffmpeg()
    ytdlp = str(YTDLP) if YTDLP.exists() else "yt-dlp"
    cache_dir = OUT_DIR / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    vid_m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    vid = vid_m.group(1) if vid_m else slug(url)
    full_tpl = str(cache_dir / f"{vid}.%(ext)s")

    if not list(cache_dir.glob(f"{vid}.*")):
        dl = [
            ytdlp,
            "--ffmpeg-location",
            ff,
            "-f",
            "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "-o",
            full_tpl,
            url,
        ]
        proc = subprocess.run(dl, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp download failed:\n{proc.stderr[-2500:]}")

    candidates = sorted(cache_dir.glob(f"{vid}.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise RuntimeError("no cached download")
    src = candidates[0]
    dur = t1 - t0
    enc = [
        ff,
        "-ss",
        str(t0),
        "-i",
        str(src),
        "-t",
        str(dur),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        "-y",
        str(out),
    ]
    if not reencode:
        enc = [ff, "-ss", str(t0), "-i", str(src), "-t", str(dur), "-c", "copy", "-y", str(out)]
    proc2 = subprocess.run(enc, capture_output=True, text=True)
    if proc2.returncode != 0:
        raise RuntimeError(f"ffmpeg cut failed:\n{proc2.stderr[-1500:]}")

    if not out.exists() or out.stat().st_size < 10_000:
        raise RuntimeError(f"output too small or missing: {out}")
    return out


def run_pilot() -> list[Path]:
    pilots = [
        ("https://www.youtube.com/watch?v=92-xf--nx88", "0:00", "2:45", "161_sfg_swing.mp4"),
        ("https://www.youtube.com/watch?v=0bWRPC49-KI", "0:00", "2:47", "173_tgu_basics.mp4"),
        ("https://www.youtube.com/watch?v=92-xf--nx88", "11:00", "14:20", "167_sfg_snatch.mp4"),
    ]
    done: list[Path] = []
    for url, start, end, name in pilots:
        out = OUT_DIR / name
        print(f"→ {name} ({start}–{end})")
        try:
            cut_clip(url, start, end, out, reencode=True)
            print(f"  OK {out.stat().st_size // 1024} KiB")
            done.append(out)
        except Exception as e:
            print(f"  FAIL: {e}", file=sys.stderr)
    return done


def from_matrix(limit: int | None = None) -> None:
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    n = 0
    for entry in data["entries"]:
        for clip in entry.get("clips", []):
            if clip.get("status") == "done" and clip.get("file"):
                continue
            if limit is not None and n >= limit:
                return
            out_name = f"{entry['display_num']:03d}_{slug(clip['label'])}.mp4"
            out = OUT_DIR / out_name
            print(f"→ #{entry['display_num']} {clip['label']}")
            try:
                cut_clip(clip["source_url"], clip["start"], clip["end"], out, reencode=True)
                rel = str(out.relative_to(ROOT))
                clip["file"] = rel
                clip["status"] = "done"
                print(f"  OK → {rel}")
                n += 1
            except Exception as e:
                clip["status"] = "error"
                clip["error"] = str(e)[:500]
                print(f"  FAIL: {e}", file=sys.stderr)
    MATRIX.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated matrix ({n} clips)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true", help="3 пилотных клипа")
    ap.add_argument("--from-matrix", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--url")
    ap.add_argument("--start", default="0:00")
    ap.add_argument("--end", default="1:00")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if args.pilot:
        run_pilot()
        return
    if args.from_matrix:
        from_matrix(args.limit)
        return
    if not args.url or not args.out:
        ap.error("need --url and --out, or --pilot / --from-matrix")
    cut_clip(args.url, args.start, args.end, args.out, reencode=True)
    print(args.out)


if __name__ == "__main__":
    main()
