#!/usr/bin/env python3
"""Стилизация своих видео Штерна под грубый комик (ffmpeg) + матрица очереди.

Съёмка: телефон, гиря 16–24 кг, фон без «фитнес-глянца» (кабинет / стена).

  ./venv/bin/python tools/stern_comic_video_pipeline.py init-matrix
  ./venv/bin/python tools/stern_comic_video_pipeline.py stylize \\
      --id comic_002_swing --raw media/stern/comic_raw/swing.mp4
  ./venv/bin/python tools/stern_comic_video_pipeline.py list

Опционально: STERN_COMIC_STYLE=domoai — после stylize выводится напоминание
прогнать файл через DomoAI/ComfyUI вручную и положить в comic_clips/.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "data" / "stern_comic_video_matrix.json"
RAW_DIR = ROOT / "media" / "stern" / "comic_raw"
OUT_DIR = ROOT / "media" / "stern" / "comic_clips"

sys.path.insert(0, str(ROOT / "tools"))
from stern_comic_breakdowns import EXERCISES  # noqa: E402

# Грубый ч/б комикс: контраст + контуры (без внешних API).
COMIC_VF = (
    "format=gray,"
    "eq=contrast=1.45:brightness=0.04,"
    "edgedetect=mode=colormix:high=0.35:low=0.08,"
    "negate"
)
MAX_DURATION_SEC = 50.0


def _ffmpeg() -> str:
    for c in ("/usr/bin/ffmpeg", "ffmpeg"):
        try:
            subprocess.run([c, "-version"], capture_output=True, check=True)
            return c
        except Exception:
            pass
    return "ffmpeg"


def video_duration(path: Path) -> float:
    ff = _ffmpeg()
    out = subprocess.run([ff, "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out.stderr or "")
    if not m:
        raise RuntimeError(f"no duration for {path}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def stylize_video(src: Path, dst: Path, *, max_sec: float = MAX_DURATION_SEC) -> None:
    ff = _ffmpeg()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dur = min(video_duration(src), max_sec)
    cmd = [
        ff,
        "-y",
        "-i",
        str(src),
        "-t",
        str(dur),
        "-vf",
        COMIC_VF,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout)[-2500:])
    if not dst.is_file() or dst.stat().st_size < 4096:
        raise RuntimeError(f"output too small: {dst}")


def build_body_html(ex: dict, clip_rel: str) -> str:
    cues = ex.get("key_cues") or []
    errors = ex.get("common_errors") or []
    lines = [
        f"🏛️ <b>{ex['headline']}</b>",
        "",
        f"<b>Упражнение:</b> {ex['exercise']}",
        "",
        ex["commentary"].strip(),
    ]
    if cues:
        lines += ["", "<b>На что смотреть:</b>"] + [f"• {c}" for c in cues[:4]]
    if errors:
        lines += ["", "<b>Типичный провал:</b>"] + [f"• {e}" for e in errors[:3]]
    lines += ["", f"#снегири #{ex['slug']} #техника #гири #штерн"]
    return "\n".join(lines)


def matrix_entry(ex: dict, *, status: str = "pending", clip_rel: str | None = None) -> dict:
    rel = clip_rel or f"media/stern/comic_clips/{ex['id']}.mp4"
    return {
        "id": ex["id"],
        "slug": ex["slug"],
        "exercise": ex["exercise"],
        "headline": ex["headline"],
        "filming": ex.get("filming", ""),
        "status": status,
        "key_cues": ex.get("key_cues", []),
        "common_errors": ex.get("common_errors", []),
        "commentary": ex.get("commentary", ""),
        "clip_file": rel if status == "ready" else None,
        "body_html": build_body_html(ex, rel),
        "style": os.getenv("STERN_COMIC_STYLE", "ffmpeg_sketch"),
    }


def init_matrix() -> None:
    entries = [matrix_entry(ex, status="pending") for ex in EXERCISES]
    data = {
        "_comment": "Еженедельное комик-видео Штерна. Пайплайн: tools/stern_comic_video_pipeline.py",
        "rubric": "comic_technique",
        "slot": "Saturday 15:00 MSK",
        "entries": entries,
    }
    MATRIX.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Matrix → {MATRIX} ({len(entries)} entries, status=pending)")


def load_matrix() -> dict:
    if not MATRIX.is_file():
        init_matrix()
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def save_matrix(data: dict) -> None:
    MATRIX.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_entry(data: dict, entry_id: str) -> dict | None:
    for e in data.get("entries") or []:
        if e.get("id") == entry_id:
            return e
    return None


def stylize_one(entry_id: str, raw: Path) -> None:
    if not raw.is_file():
        raise SystemExit(f"raw not found: {raw}")
    data = load_matrix()
    entry = find_entry(data, entry_id)
    if not entry:
        raise SystemExit(f"unknown id {entry_id!r} — run init-matrix")
    out = OUT_DIR / f"{entry_id}.mp4"
    print(f"Stylize {raw.name} → {out.name}")
    stylize_video(raw, out)
    rel = str(out.relative_to(ROOT))
    ex = next((x for x in EXERCISES if x["id"] == entry_id), None)
    if ex:
        updated = matrix_entry(ex, status="ready", clip_rel=rel)
        entry.update(updated)
    else:
        entry["status"] = "ready"
        entry["clip_file"] = rel
    save_matrix(data)
    print(f"OK ready → {rel} ({out.stat().st_size // 1024} KB)")
    if os.getenv("STERN_COMIC_STYLE", "").lower() in ("domoai", "comfyui", "api"):
        print(
            f"\nДополнительно: прогоните {out} через DomoAI/ComfyUI (комикс-стиль) "
            f"и замените файл тем же путём."
        )


def cmd_list(_: argparse.Namespace) -> None:
    data = load_matrix()
    for e in data.get("entries") or []:
        clip = e.get("clip_file") or "—"
        print(f"{e.get('status', '?'):8} {e.get('id')}  {clip}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Штерн комик-видео: матрица и стилизация")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-matrix", help="создать/пересоздать матрицу из EXERCISES")

    p_st = sub.add_parser("stylize", help="ffmpeg-комик из raw mp4")
    p_st.add_argument("--id", required=True, help="comic_002_swing")
    p_st.add_argument("--raw", required=True, type=Path, help="media/stern/comic_raw/swing.mp4")

    sub.add_parser("list", help="статусы записей")

    args = ap.parse_args()
    if args.cmd == "init-matrix":
        init_matrix()
    elif args.cmd == "stylize":
        stylize_one(args.id, args.raw if args.raw.is_absolute() else ROOT / args.raw)
    elif args.cmd == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
