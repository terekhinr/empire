#!/usr/bin/env python3
"""Full book: Harford Undercover Economist → Edge TTS MP3 → Telegram parts."""
from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from empire_notify import send, send_file  # noqa: E402
from harford_undercover_ch1_tts import (  # noqa: E402
    INLINE_NOTES,
    INTRO_BRIEF_NOTES,
    apply_lexicon,
    extract_pages,
    fix_all_caps_runs,
    fix_pdf_artifacts,
    inject_inline_notes,
    strip_toc_bleed,
    trim_annotation,
)
from prepare_md_for_tts import prepare_for_tts  # noqa: E402

PDF = ROOT / "data" / "book" / "Тим Харфорд Экономист под прикрытием.pdf"
OUT_DIR = ROOT / "data" / "audio" / "harford_undercover"
STEM = "ekonomist_pod_prikrytiem_FULL"
EDGE = ROOT / "scripts" / "docx_to_mp3_edge.py"
PY = ROOT / "venv" / "bin" / "python3"
TG_MAX = 47 * 1024 * 1024

# 0-based page ranges [start, end)
SECTIONS: list[tuple[str, int, int]] = [
    ("annotation", 1, 2),
    ("intro", 7, 10),
    ("ch01", 10, 32),
    ("ch02", 32, 59),
    ("ch03", 59, 76),
    ("ch04", 76, 104),
    ("ch05", 104, 129),
    ("ch06", 129, 146),
    ("ch07", 146, 165),
    ("ch08", 165, 186),
    ("ch09", 186, 214),
    ("ch10", 214, 235),
]

CHAPTER_WORDS = {
    1: "первая",
    2: "вторая",
    3: "третья",
    4: "четвёртая",
    5: "пятая",
    6: "шестая",
    7: "седьмая",
    8: "восьмая",
    9: "девятая",
    10: "десятая",
}

EXTRA_LEXICON: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bDell\b"), "Делл"),
    (re.compile(r"\bCompaq\b"), "Компак"),
    (re.compile(r"\bFTSE\b"), "эф ти эс и"),
    (re.compile(r"\bDow\b"), "Доу"),
    (re.compile(r"\bUSAID\b"), "ю эс эйд"),
    (re.compile(r"\bОЭСР\b"), "о э с эр"),
    (re.compile(r"\bTransparency International\b"), "Транспэренси Интернэшнл"),
    (re.compile(r"\bFederal Reserve\b"), "Федеральный резерв"),
    (re.compile(r"\bАлан(?:а|у)? Гринспен\b"), "Алан Гринспен"),
    (re.compile(r"\bМервин(?:а|у)? Кинг\b"), "Мервин Кинг"),
    (re.compile(r"\bкукиз\b", re.I), "куки"),
    (re.compile(r"\bcookies\b", re.I), "куки"),
]


def expand_inline_notes() -> None:
    """Brief spoken asides for remaining markers (no bibliographic URLs)."""
    extras = {
        "5": "Речь о лондонском Куполе тысячелетия.",
        "6": "Куки — файлы, по которым сайт узнаёт посетителя.",
        "7": "Счастливый час — время сниженных цен.",
        "8": "Алан Гринспен — бывший глава Федеральной резервной системы США.",
        "9": "Мервин Кинг — бывший управляющий Банка Англии.",
        "10": "Dell и Компак — производители компьютеров.",
        "11": "Сбой рыночного механизма — ситуация, когда рынок сам не даёт лучшего результата.",
        "12": "Имеется в виду эпидемия холеры в Лондоне девятнадцатого века.",
        "13": "Оценка американского природоохранного ведомства.",
        "14": "То же ведомство — про борьбу с кислотными дождями.",
        "15": "О мерах против климатических изменений.",
        "16": "Цитата из Джерома К. Джерома.",
        "17": "Британская организация поддержки слепых.",
        "18": "Британский институт оценки медицинских технологий.",
        "19": "О границах предсказуемости рынков.",
        "20": "Оценка масштаба рынка.",
        "21": "Прозвище экономиста-пессимиста.",
        "22": "Книга о крахе на Уолл-стрит.",
        "23": "Книга с прогнозом Доу тридцать шесть тысяч.",
        "24": "Классическая книга по теории игр.",
        "25": "Учебный пример из теории игр.",
        "26": "Аукцион Викри — аукцион второй цены.",
        "27": "Об участнике аукциона лицензий.",
        "28": "Рейтинг коррупции Transparency International.",
        "29": "Отсылка к фильму Рождённая свободной.",
        "30": "Британская добровольческая организация.",
        "31": "Сравнение с Сиднейским оперным театром.",
        "32": "Агентство США по международному развитию.",
        "33": "Книга Стечение обстоятельств.",
        "34": "Статистика мировой торговли.",
        "35": "Гонка уступок — конкуренция стран за инвестиции ценой ослабления норм.",
        "36": "Организация экономического сотрудничества и развития.",
        "37": "Шутка про экономистов, которые всегда добавляют с другой стороны.",
        "38": "О санкциях США против Кубы.",
        "39": "Сравнение с Центральным парком Нью-Йорка.",
        "40": "Сравнение с небоскрёбом Крайслер-билдинг.",
        "41": "Сравнение производительности труда.",
        "42": "Отклик на книгу Мартина Вулфа о глобализации.",
    }
    INLINE_NOTES.update(extras)


def chapterize_headings(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        n = int(m.group(1))
        word = CHAPTER_WORDS.get(n, str(n))
        return f"Глава {word}."

    text = re.sub(r"Глава\s+(\d+)\b", repl, text)
    return text


def apply_extra_lexicon(text: str) -> str:
    for pat, repl in EXTRA_LEXICON:
        text = pat.sub(repl, text)
    return text


def build_full_manuscript(pdf: Path) -> str:
    expand_inline_notes()
    chunks: list[str] = [
        "Тим Харфорд. Экономист под прикрытием.\n\n"
        "Полная аудиокнига. Аннотация, введение и десять глав.\n"
        "Библиографические примечания в конце книги опущены; "
        "короткие пояснения даны по ходу текста.\n"
    ]

    for key, start, end in SECTIONS:
        raw = fix_pdf_artifacts(extract_pages(pdf, start, end))
        if key == "annotation":
            raw = trim_annotation(raw)
        raw = inject_inline_notes(raw)
        if key == "intro":
            body = raw.strip()
            if not body.lower().startswith("введение"):
                body = "Введение.\n\n" + body
            body += f"\n\n{INTRO_BRIEF_NOTES}\n"
            chunks.append(body)
        else:
            chunks.append(raw.strip())

    raw = "\n\n".join(c for c in chunks if c.strip())
    raw = strip_toc_bleed(raw)
    raw = fix_all_caps_runs(raw)
    raw = chapterize_headings(raw)
    raw = apply_lexicon(raw)
    raw = apply_extra_lexicon(raw)
    cleaned = prepare_for_tts(raw)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"


def duration_sec(path: Path) -> float:
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


def split_for_telegram(mp3: Path, tmp_dir: Path) -> list[Path]:
    size = mp3.stat().st_size
    if size <= TG_MAX:
        return [mp3]
    parts_n = math.ceil(size / TG_MAX)
    dur = duration_sec(mp3)
    if dur <= 0:
        raise RuntimeError("cannot read mp3 duration")
    seg = dur / parts_n
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
            str(seg),
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


def synth_edge(text_path: Path, mp3_path: Path, workers: int = 3) -> int:
    cmd = [
        str(PY),
        str(EDGE),
        str(text_path),
        "-o",
        str(mp3_path),
        "--voice",
        "ru-RU-DmitryNeural",
        "--workers",
        str(workers),
        "--resume",
        "--keep-chunks",
        "--skip-preflight",
    ]
    print(" ".join(cmd), flush=True)
    return subprocess.call(cmd)


def deliver(mp3: Path) -> bool:
    dur_min = duration_sec(mp3) / 60
    size_mb = mp3.stat().st_size / (1024 * 1024)
    label = "Харфорд — Экономист под прикрытием (полная)"
    send(
        f"✅ Полная озвучка готова: {label}\n"
        f"{dur_min:.0f} мин · {size_mb:.0f} МБ\n"
        f"Движок: Edge Dmitry. Сейчас пришлю частями…"
    )
    with tempfile.TemporaryDirectory(prefix="tg_harford_") as tmp:
        parts = split_for_telegram(mp3, Path(tmp))
        total = len(parts)
        for i, part in enumerate(parts, start=1):
            cap = label if total == 1 else f"{label} — часть {i}/{total}"
            if not send_file(part, caption=cap, as_audio=True):
                send(f"❌ Не удалось отправить часть {i}/{total}.")
                return False
            time.sleep(1.5)
    send(f"✅ Все {total} частей отправлены.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=PDF)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--synth-only", action="store_true")
    parser.add_argument("--send-only", action="store_true")
    parser.add_argument("--no-send", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    text_path = args.out_dir / f"{STEM}_tts.txt"
    mp3_path = args.out_dir / f"{STEM}.mp3"
    log_path = args.out_dir / "full_synth.log"

    if not args.synth_only and not args.send_only:
        manuscript = build_full_manuscript(args.pdf)
        text_path.write_text(manuscript, encoding="utf-8")
        print(f"TTS text: {text_path} ({len(manuscript)} chars)", flush=True)

    if args.prepare_only:
        return 0

    if not args.send_only:
        send(
            "🎙 Харфорд «Экономист под прикрытием»: полная озвучка "
            "(Edge Dmitry, ~9–10 часов аудио). Это займёт около 1–2 часов — "
            "потом пришлю в этот чат частями."
        )
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"\n=== start {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        rc = synth_edge(text_path, mp3_path, workers=args.workers)
        if rc != 0:
            send(f"❌ Ошибка полной озвучки Харфорда (код {rc}). См. full_synth.log")
            return rc

    if args.no_send:
        print(f"MP3 ready: {mp3_path}")
        return 0

    if not mp3_path.is_file() or mp3_path.stat().st_size < 1_000_000:
        send("❌ MP3 полной книги не найден или слишком маленький.")
        return 1

    return 0 if deliver(mp3_path) else 2


if __name__ == "__main__":
    raise SystemExit(main())
