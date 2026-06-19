#!/usr/bin/env python3
"""Скачать 40 шортсов гиревиков, наложить субтитры, собрать матрицу с разборами.

  ./venv/bin/python tools/stern_technique_pipeline.py           # всё
  ./venv/bin/python tools/stern_technique_pipeline.py --limit 3 # пилот
  ./venv/bin/python tools/stern_technique_pipeline.py --matrix-only
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_MATRIX = ROOT / "data" / "stern_technique_matrix_161_200.json"
CLIP_DIR = ROOT / "media" / "stern" / "technique_clips"
SUB_DIR = ROOT / "media" / "stern" / "technique_subs"
YTDLP = ROOT / "venv" / "bin" / "yt-dlp"

sys.path.insert(0, str(ROOT / "tools"))
from stern_technique_sources import SOURCES  # noqa: E402
from stern_technique_breakdowns import BREAKDOWNS  # noqa: E402


def _ffmpeg() -> str:
    for c in ("/usr/bin/ffmpeg", "ffmpeg"):
        try:
            subprocess.run([c, "-version"], capture_output=True, check=True)
            return c
        except Exception:
            pass
    return "ffmpeg"


def parse_ts(ts: str) -> float:
    parts = [float(x) for x in ts.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(ts)


def fmt_ts(sec: float) -> str:
    """SRT: HH:MM:SS,mmm"""
    if sec < 0:
        sec = 0.0
    ms = int(round((sec % 1) * 1000))
    total = int(sec)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def video_duration(path: Path) -> float:
    ff = _ffmpeg()
    out = subprocess.run(
        [ff, "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out.stderr or "")
    if not m:
        raise RuntimeError(f"no duration for {path}")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def ytdlp_download(vid: str, out_tpl: Path) -> Path:
    url = f"https://www.youtube.com/watch?v={vid}"
    ytdlp = str(YTDLP) if YTDLP.exists() else "yt-dlp"
    ff = _ffmpeg()
    cmd = [
        ytdlp,
        "--ffmpeg-location",
        ff,
        "-f",
        "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "-o",
        str(out_tpl),
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:])
    files = list(out_tpl.parent.glob(out_tpl.name.replace("%(ext)s", "*")))
    if not files:
        files = list(out_tpl.parent.glob(f"{vid}.*"))
    if not files:
        raise RuntimeError(f"download missing for {vid}")
    return sorted(files, key=lambda p: p.stat().st_mtime)[-1]


def cut_video(src: Path, start: float, end: float, dst: Path) -> None:
    ff = _ffmpeg()
    dur = end - start
    cmd = [
        ff,
        "-ss",
        str(start),
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
        str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-1500:])


def write_srt(lines: list[tuple[float, float, str]], path: Path) -> None:
    chunks = []
    for i, (t0, t1, text) in enumerate(lines, 1):
        text = textwrap.fill(text, 42)
        chunks.append(f"{i}\n{fmt_ts(t0)} --> {fmt_ts(t1)}\n{text}\n")
    # BOM помогает libass с кириллицей
    path.write_text("\ufeff" + "\n".join(chunks), encoding="utf-8")


def burn_subs(video: Path, srt: Path, out: Path) -> None:
    ff = _ffmpeg()
    style = "FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=40"
    # Относительный путь из каталога SRT — libass надёжнее открывает файл
    rel_srt = srt.name
    vf = f"subtitles={rel_srt}:force_style='{style}'"
    cmd = [
        ff,
        "-i",
        str(video.resolve()),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "copy",
        "-y",
        str(out.resolve()),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(srt.parent.resolve()))
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-1500:])


def subtitle_lines(num: int, bd: dict, duration: float) -> list[tuple[float, float, str]]:
    cues = bd.get("subtitle_cues") or []
    if not cues:
        return []
    n = len(cues)
    slot = duration / n
    lines = []
    for i, cue in enumerate(cues):
        t0 = i * slot + 0.05
        t1 = min(duration - 0.05, (i + 1) * slot)
        lines.append((t0, t1, cue))
    return lines


def build_body_html(src: dict, bd: dict, clip_sub: str) -> str:
    tag = src["slug"][:24]
    parts = [
        f"🏛️ <b>{src['headline']}</b>",
        "",
        f"<b>Атлет:</b> {src['athlete']}",
        f"<b>Упражнение:</b> {src['exercise']}",
        "",
        f"<b>Суть движения.</b> {bd['essence']}",
        "",
        "<b>Ключевые акценты:</b>",
        "\n".join(f"• {c}" for c in bd["key_cues"]),
        "",
        "<b>Типичные ошибки.</b>",
        "\n".join(f"• {e}" for e in bd["common_errors"]),
        "",
        f"<b>Разбор видео.</b> {bd['video_breakdown']}",
        "",
        f"<b>Связь с наследием.</b> {bd['legacy_link']}",
        "",
        f"🎬 <i>Клип с субтитрами: {clip_sub}</i>",
        f"<i>Источник видео: {src['athlete']} — YouTube ({src['youtube_id']})</i>",
        "",
        f"#снегири #{tag} #техника #гири #гиревойспорт",
    ]
    return "\n".join(parts)


def process_one(src: dict, *, skip_download: bool = False) -> dict:
    num = src["num"]
    bd = BREAKDOWNS[num]
    base = CLIP_DIR / f"{num:03d}_{src['slug']}"
    raw = base.with_suffix(".raw.mp4")
    cut = base.with_suffix(".mp4")
    sub_video = base.with_name(base.name + "_sub").with_suffix(".mp4")
    srt = SUB_DIR / f"{num:03d}_{src['slug']}.srt"

    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    SUB_DIR.mkdir(parents=True, exist_ok=True)

    cache = CLIP_DIR / "_cache" / f"{src['youtube_id']}.%(ext)s"
    cache.parent.mkdir(parents=True, exist_ok=True)

    if not skip_download:
        vid_key = src["youtube_id"].lstrip("-")
        cached = list(cache.parent.glob(f"{src['youtube_id']}.*"))
        if not cached:
            cached = list(cache.parent.glob(f"{vid_key}.*"))
        if not cached:
            ytdlp_download(src["youtube_id"], cache)
            cached = list(cache.parent.glob(f"{src['youtube_id']}.*")) or list(
                cache.parent.glob(f"{vid_key}.*")
            )
        src_file = cached[-1]

        if src.get("cut"):
            t0 = parse_ts(src["cut"][0])
            t1 = parse_ts(src["cut"][1])
            cut_video(src_file, t0, t1, cut)
        else:
            subprocess.run(["cp", "-f", str(src_file), str(cut)], check=True)

        dur = video_duration(cut)
        sub_lines = subtitle_lines(num, bd, dur)
        write_srt(sub_lines, srt)
        burn_subs(cut, srt, sub_video)

    rel_cut = str(cut.relative_to(ROOT))
    rel_sub = str(sub_video.relative_to(ROOT))
    rel_srt = str(srt.relative_to(ROOT))

    return {
        "display_num": num,
        "id": f"technique_{num:03d}_{src['slug']}",
        "block": 7,
        "block_title": "Техника гиревого спорта — разборы чемпионов",
        "kind": "technique",
        "headline": src["headline"],
        "name": src["headline"].split(":")[0].strip(),
        "exercise": src["exercise"],
        "athlete": src["athlete"],
        "tag": src["slug"][:24],
        "status": "ready",
        "verbatim": True,
        "youtube": {
            "id": src["youtube_id"],
            "url": f"https://www.youtube.com/watch?v={src['youtube_id']}",
            "title": src["title"],
            "athlete": src["athlete"],
            "cut": src.get("cut"),
        },
        "video": {
            "raw_file": rel_cut,
            "subtitled_file": rel_sub,
            "srt_file": rel_srt,
        },
        "subtitles": bd.get("subtitle_cues", []),
        "key_cues": bd["key_cues"],
        "common_errors": bd["common_errors"],
        "commentary": bd["video_breakdown"],
        "legacy": bd["legacy_link"],
        "source": f"{src['athlete']}; YouTube {src['youtube_id']}",
        "body_html": build_body_html(src, bd, rel_sub),
        "clip_file": rel_sub,
        "note_id_conflict": f"legacy_{num:03d}_* в очереди биографий; id technique_{num:03d}_*",
    }


def build_matrix(entries: list[dict]) -> dict:
    return {
        "_comment": "40 разборов техники #161–#200. Видео: гиревики блока 5. Пайплайн: tools/stern_technique_pipeline.py",
        "rubric": "athletic_legacy",
        "display_range": [161, 200],
        "kind": "technique",
        "video_policy": "YouTube shorts/клипы атлетов из постов (Руднев, Денисов, Анасенко, Хвостов, Мишин, Васильев, Блуд, Дедюхина и др.)",
        "entries": entries,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--matrix-only", action="store_true", help="только JSON без скачивания")
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    rows = SOURCES[: args.limit] if args.limit else SOURCES
    entries = []
    for i, src in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] #{src['num']} {src['headline']}")
        try:
            if args.matrix_only:
                bd = BREAKDOWNS[src["num"]]
                e = process_one(src, skip_download=True)
                # placeholder paths
                e["status"] = "matrix"
                e["video"] = {"subtitled_file": None, "srt_file": None}
                e.pop("body_html", None)
                e["body_html"] = build_body_html(src, bd, f"media/stern/technique_clips/{src['num']:03d}_{src['slug']}_sub.mp4")
            else:
                e = process_one(src, skip_download=args.skip_download)
            entries.append(e)
            print(f"  OK → {e['video'].get('subtitled_file') or 'matrix'}")
        except Exception as ex:
            print(f"  FAIL: {ex}", file=sys.stderr)
            bd = BREAKDOWNS[src["num"]]
            entries.append(
                {
                    "display_num": src["num"],
                    "id": f"technique_{src['num']:03d}_{src['slug']}",
                    "status": "error",
                    "error": str(ex)[:500],
                    "youtube": {"id": src["youtube_id"], "url": f"https://www.youtube.com/watch?v={src['youtube_id']}"},
                    "headline": src["headline"],
                    "body_html": build_body_html(src, bd, "pending"),
                }
            )

    OUT_MATRIX.write_text(json.dumps(build_matrix(entries), ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for e in entries if e.get("status") == "ready")
    print(f"\nDone: {ok}/{len(entries)} ready → {OUT_MATRIX}")


if __name__ == "__main__":
    main()
