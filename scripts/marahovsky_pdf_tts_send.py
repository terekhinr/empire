#!/usr/bin/env python3
"""Extract Marahovsky PDFs → clean TTS text → edge MP3 → Telegram."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from empire_notify import send, send_file  # noqa: E402
from prepare_md_for_tts import prepare_for_tts  # noqa: E402

DEFAULT_DIR = ROOT / "data" / "audio" / "marahovsky"
PY = ROOT / "venv" / "bin" / "python3"
EDGE = ROOT / "scripts" / "docx_to_mp3_edge.py"

META_LINE = re.compile(
    r"^\s*(?:\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|"
    r"сентября|октября|ноября|декабря).*"
    r"|\d+\s*минут[аы]?\s*)$",
    re.I,
)

EXTRA = (
    (re.compile(r"\bуважаемый друзей\b", re.I), "уважаемых друзей"),
    (re.compile(r"\bт\.к\.\b", re.I), "так как"),
    (re.compile(r"\bX лет\b"), "несколько лет"),
    (re.compile(r"\bN лет\b"), "много лет"),
)

BODY_START = re.compile(
    r"^(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье|"
    r"Сегодня|«|\"|Ув\.|уважаем)",
    re.I,
)


def slugify(name: str) -> str:
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r"_Marahovsky(?:_Sponsr)?$", "", name, flags=re.I)
    name = re.sub(r"[^\w\s\-а-яА-ЯёЁ]+", "", name, flags=re.U)
    name = re.sub(r"[\s\-]+", "_", name).strip("_")
    return name[:80] or "article"


def pdf_to_raw(pdf: Path) -> tuple[str, str]:
    doc = fitz.open(pdf)
    lines: list[str] = []
    for page in doc:
        for line in page.get_text("text").splitlines():
            line = line.replace("\u00ad", "").rstrip()
            if line.strip():
                lines.append(line.strip())

    joined: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        while i + 1 < len(lines) and cur.endswith("-") and lines[i + 1][:1].islower():
            cur = cur[:-1] + lines[i + 1]
            i += 1
        while (
            i + 1 < len(lines)
            and not cur.endswith((".", "!", "?", ":", ";", "»", '"', "“"))
            and lines[i + 1][:1].islower()
        ):
            cur = cur + " " + lines[i + 1]
            i += 1
        joined.append(cur)
        i += 1

    while joined and META_LINE.match(joined[0]):
        joined.pop(0)

    title = joined[0] if joined else unicodedata.normalize("NFC", pdf.stem)
    body_start = 1
    raw = f"# {title}\n\n" + "\n\n".join(joined[body_start:])
    raw = unicodedata.normalize("NFC", raw)
    raw = "".join(ch for ch in raw if unicodedata.category(ch)[0] != "C" or ch in "\n\t")
    return title, raw


def clean_for_speech(raw: str) -> str:
    text = prepare_for_tts(raw)
    for pat, repl in EXTRA:
        text = pat.sub(repl, text)
    paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    text = "\n\n".join(p for p in paras if p)
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip() + "\n"


def synth(txt: Path, mp3: Path) -> None:
    subprocess.run(
        [
            str(PY),
            str(EDGE),
            str(txt),
            "-o",
            str(mp3),
            "--skip-preflight",
            "--workers",
            "4",
        ],
        check=True,
        cwd=str(ROOT / "scripts"),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--pdf", type=Path, action="append", help="Process only this PDF (repeatable)")
    ap.add_argument("--only-new", action="store_true", help="Only PDFs without a matching MP3 yet")
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument("--skip-existing", action="store_true", help="Skip synth if MP3 already exists")
    ap.add_argument("--no-resend", action="store_true", help="With --skip-existing, do not re-send existing MP3")
    args = ap.parse_args()

    out_dir = args.dir.expanduser().resolve()
    if args.pdf:
        pdfs = [p.expanduser().resolve() for p in args.pdf]
        missing = [str(p) for p in pdfs if not p.is_file()]
        if missing:
            print(f"Missing PDF: {missing}", file=sys.stderr)
            return 1
    else:
        pdfs = sorted(out_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs in {out_dir}", file=sys.stderr)
        return 1

    print(f"Found {len(pdfs)} PDFs in {out_dir}", flush=True)
    if not args.no_telegram:
        send(f"🎙 Marahovsky: озвучка {len(pdfs)} статей → MP3 и отправка в бот.")

    jobs: list[tuple[Path, str, Path, bool]] = []
    for pdf in pdfs:
        title, raw = pdf_to_raw(pdf)
        slug = slugify(title)
        raw_path = out_dir / f"{slug}.full.txt"
        tts_path = out_dir / f"{slug}_tts.txt"
        mp3_path = out_dir / f"{slug}.mp3"
        cleaned = clean_for_speech(raw)
        raw_path.write_text(raw, encoding="utf-8")
        tts_path.write_text(cleaned, encoding="utf-8")
        print(f"TXT {slug}: raw={len(raw)} clean={len(cleaned)}", flush=True)
        exists = mp3_path.is_file() and mp3_path.stat().st_size > 50_000
        if args.only_new and exists:
            print(f"SKIP already has MP3: {mp3_path.name}", flush=True)
            continue
        jobs.append((mp3_path, title, tts_path, exists))

    if not jobs:
        print("Nothing to process", flush=True)
        return 0

    ok = 0
    for mp3_path, title, tts_path, existed in jobs:
        need_synth = not (args.skip_existing and existed)
        if need_synth:
            print(f"SYNTH: {title}", flush=True)
            try:
                synth(tts_path, mp3_path)
            except Exception as exc:
                print(f"FAIL synth {title}: {exc}", flush=True)
                if not args.no_telegram:
                    send(f"❌ Ошибка озвучки: {title}")
                continue
        else:
            print(f"REUSE: {mp3_path.name}", flush=True)
            if args.no_resend:
                ok += 1
                continue

        if args.no_telegram:
            ok += 1
            continue

        size = mp3_path.stat().st_size / 1024 / 1024
        print(f"SEND: {mp3_path.name} ({size:.1f} MB)", flush=True)
        if send_file(mp3_path, caption=f"Мараховский: {title}", as_audio=True):
            ok += 1
            print(f"OK telegram: {title}", flush=True)
        else:
            send(f"❌ Не удалось отправить: {title}")
            print(f"FAIL telegram: {title}", flush=True)

    if not args.no_telegram:
        send(f"Готово: {ok}/{len(jobs)} MP3 Мараховского отправлено.")
    print(f"DONE {ok}/{len(jobs)}", flush=True)
    return 0 if ok == len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
