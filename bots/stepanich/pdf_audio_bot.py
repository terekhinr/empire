#!/usr/bin/env python3
"""Telegram bot helpers: PDF -> cleaned Russian speech -> MP3 parts.

TTS providers:
  PDF_AUDIO_TTS_PROVIDER=edge   (default, Microsoft Edge TTS; ударения свои)
  PDF_AUDIO_TTS_PROVIDER=yandex (Yandex SpeechKit; нативные ударения `+`)
  PDF_AUDIO_TTS_PROVIDER=silero (Silero TTS + silero-stress `+`; верные ударения RU)
  PDF_AUDIO_TTS_PROVIDER=gemini (Gemini TTS; сейчас часто 500)
  PDF_AUDIO_TTS_PROVIDER=auto   (сначала Gemini, при сбое → edge)
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path

import fitz
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
MEDIA_ROOT = ROOT / "media" / "pdf_audio_bot"
EDGE_SCRIPT = ROOT / "scripts" / "docx_to_mp3_edge.py"
SILERO_SCRIPT = ROOT / "scripts" / "docx_to_mp3_silero.py"
YANDEX_SCRIPT = ROOT / "scripts" / "docx_to_mp3_yandex.py"
VENV_PYTHON = ROOT / "venv" / "bin" / "python3"

load_dotenv(ROOT / ".env")

TELEGRAM_TOKEN = os.getenv("PDF_AUDIO_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_TTS_MODEL = os.getenv("PDF_AUDIO_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_VOICE = os.getenv("PDF_AUDIO_TTS_VOICE", "charon")
TTS_PROVIDER = (os.getenv("PDF_AUDIO_TTS_PROVIDER") or "edge").strip().lower()
EDGE_VOICE = os.getenv("PDF_AUDIO_EDGE_VOICE", "ru-RU-DmitryNeural")
# Чуть медленнее нормы; сильный минус удлиняет и «хорошие» паузы.
EDGE_RATE = os.getenv("PDF_AUDIO_EDGE_RATE", "-8%")
SILERO_SPEAKER = os.getenv("PDF_AUDIO_SILERO_SPEAKER", "eugene")
YANDEX_VOICE = os.getenv("PDF_AUDIO_YANDEX_VOICE", "filipp")
YANDEX_SPEED = os.getenv("PDF_AUDIO_YANDEX_SPEED", "0.95")
MAX_PDF_MB = int(os.getenv("PDF_AUDIO_MAX_PDF_MB", "20"))
# ~30–40 мин речи на часть; Telegram audio ≤ 50 МБ
PART_TARGET_CHARS = int(os.getenv("PDF_AUDIO_PART_TARGET_CHARS", "32000"))
CHUNK_MAX_CHARS = int(os.getenv("PDF_AUDIO_CHUNK_MAX_CHARS", "2500"))
MIN_AUDIO_BYTES = int(os.getenv("PDF_AUDIO_MIN_CHUNK_BYTES", "5000"))
RETRY_COUNT = int(os.getenv("PDF_AUDIO_RETRIES", "3"))
# Если MP3 части больше — режем мельче (байты)
PART_MAX_MP3_BYTES = int(os.getenv("PDF_AUDIO_PART_MAX_MP3_BYTES", str(45 * 1024 * 1024)))
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".markdown", ".docx"}

META_LINE = re.compile(
    r"^\s*(?:\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|"
    r"сентября|октября|ноября|декабря).*"
    r"|\d+\s*минут[аы]?\s*)$",
    re.I,
)

PROMPT_PREFIX = (
    "Прочитай вслух по-русски как профессиональный диктор аудиокниги. "
    "Естественные интонации, спокойный уверенный темп, хорошая дикция. "
    "Соблюдай ударения: ударная гласная отмечена знаком ́ (акут) после буквы. "
    "Не читай сам знак ударения вслух. Текст:\n\n"
)

sys_path = str(ROOT / "scripts")
if sys_path not in os.sys.path:
    os.sys.path.insert(0, sys_path)
from prepare_md_for_tts import prepare_for_tts  # noqa: E402


@dataclass
class BookPart:
    index: int
    title: str
    text: str


CHAPTER_SPLIT = re.compile(
    r"(?mi)^(?:"
    r"#{1,3}\s+.+"
    r"|глава\s+[0-9ivxlcdmа-яё]+\b.*"
    r"|часть\s+[0-9ivxlcdmа-яё]+\b.*"
    r"|chapter\s+\d+\b.*"
    r"|part\s+\d+\b.*"
    r")$"
)


def ensure_env_loaded() -> None:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def slugify(name: str) -> str:
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r"[^\w\s\-а-яА-ЯёЁ]+", "", name, flags=re.U)
    name = re.sub(r"[\s\-]+", "_", name).strip("_")
    return name[:80] or f"book_{int(time.time())}"


def split_text(text: str, max_len: int) -> list[str]:
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
                continue
            if buf:
                chunks.append(buf)
            if len(sent) <= max_len:
                buf = sent
                continue
            for i in range(0, len(sent), max_len):
                chunks.append(sent[i : i + max_len])
            buf = ""
        if buf:
            current = buf
    if current:
        chunks.append(current)
    return chunks


def _is_chapter_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 120:
        return False
    if re.match(
        r"^(?:глава|часть|раздел|книга|том|prologue|epilogue|introduction|"
        r"введение|заключение|послесловие|предисловие|chapter|part)\b",
        s,
        re.I,
    ):
        return True
    if re.match(r"^(?:\d{1,3}|[IVXLC]{1,8})(?:\.|\)|:)\s+\S", s):
        return True
    return False


def _reflow_book_lines(lines: list[str]) -> list[str]:
    """Склеить hard-wrap строки книги в абзацы.

    Иначе каждая строка PDF становится отдельным абзацем и Edge
    делает длинную паузу между ними.
    """
    paras: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            paras.append(" ".join(buf))
            buf.clear()

    for line in lines:
        s = re.sub(r"\s+", " ", line).strip()
        if not s:
            flush()
            continue
        if _is_chapter_heading(s):
            flush()
            paras.append(s)
            continue
        buf.append(s)
    flush()
    return paras


def pdf_to_raw_text(pdf_path: Path) -> tuple[str, str]:
    doc = fitz.open(pdf_path)
    lines: list[str] = []
    for page in doc:
        for line in page.get_text("text").splitlines():
            line = line.replace("\u00ad", "").rstrip()
            if line.strip():
                lines.append(line.strip())

    merged: list[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i]
        while i + 1 < len(lines) and cur.endswith("-") and lines[i + 1][:1].islower():
            cur = cur[:-1] + lines[i + 1]
            i += 1
        while (
            i + 1 < len(lines)
            and not cur.endswith((".", "!", "?", ":", ";", '"'))
            and lines[i + 1][:1].islower()
        ):
            cur = cur + " " + lines[i + 1]
            i += 1
        merged.append(cur)
        i += 1

    while merged and META_LINE.match(merged[0]):
        merged.pop(0)

    title = merged[0] if merged else pdf_path.stem
    # PDF часто начинается с номера страницы / мусора — берём имя файла.
    if len(title) < 4 or re.fullmatch(r"\d{1,4}", title.strip()):
        title = pdf_path.stem.replace("_", " ").replace("-", " ").strip() or pdf_path.stem
    body_lines = merged[1:] if len(merged) > 1 else list(merged)
    body = "\n\n".join(_reflow_book_lines(body_lines))
    raw = f"# {title}\n\n{body}".strip() + "\n"
    raw = unicodedata.normalize("NFC", raw)
    raw = "".join(ch for ch in raw if unicodedata.category(ch)[0] != "C" or ch in "\n\t")
    return title, raw


def plain_to_raw_text(path: Path) -> tuple[str, str]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = unicodedata.normalize("NFC", raw).strip() + "\n"
    title = path.stem
    for line in raw.splitlines():
        s = line.strip().lstrip("#").strip()
        if s:
            title = s[:120]
            break
    # Hard-wrap txt/md без пустых строк → один поток (иначе паузы на каждой строке)
    if raw.count("\n\n") < 2 and raw.count("\n") > 8:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if lines and lines[0].startswith("#"):
            head = lines[0]
            body = "\n\n".join(_reflow_book_lines(lines[1:]))
            raw = f"{head}\n\n{body}\n"
        else:
            raw = f"# {title}\n\n" + "\n\n".join(_reflow_book_lines(lines)) + "\n"
    elif not raw.lstrip().startswith("#"):
        raw = f"# {title}\n\n{raw}"
    return title, raw


def docx_to_raw_text(path: Path) -> tuple[str, str]:
    from docx import Document

    paras = [p.text.strip() for p in Document(str(path)).paragraphs if p.text.strip()]
    title = paras[0][:120] if paras else path.stem
    body = "\n\n".join(paras[1:] if len(paras) > 1 else paras)
    raw = f"# {title}\n\n{body}".strip() + "\n"
    return title, unicodedata.normalize("NFC", raw)


def load_source_text(path: Path) -> tuple[str, str]:
    """Вернуть (title, raw_text) из pdf/txt/md/docx."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return pdf_to_raw_text(path)
    if suffix in {".txt", ".md", ".markdown"}:
        return plain_to_raw_text(path)
    if suffix == ".docx":
        return docx_to_raw_text(path)
    raise RuntimeError(f"Неподдерживаемый формат: {suffix}. Нужны: {', '.join(sorted(SUPPORTED_SUFFIXES))}")


def clean_for_tts(raw: str) -> str:
    # Silero / Yandex: `п+окер`. Gemini: U+0301. Edge ударения по сути игнорирует.
    if TTS_PROVIDER in ("silero", "yandex"):
        os.environ["PDF_AUDIO_STRESS_FORMAT"] = "plus"
        os.environ.setdefault("PDF_AUDIO_STRESS", "1")
    elif TTS_PROVIDER == "gemini":
        os.environ["PDF_AUDIO_STRESS_FORMAT"] = "acute"
        os.environ.setdefault("PDF_AUDIO_STRESS", "1")
    text = prepare_for_tts(raw)
    paragraphs = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    text = "\n\n".join(p for p in paragraphs if p)
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip() + "\n"


def render_part_yandex(part: BookPart, workdir: Path, stem: str) -> Path:
    """Озвучка части через Yandex SpeechKit (ударения `+` нативно)."""
    if not YANDEX_SCRIPT.is_file():
        raise RuntimeError(f"Нет yandex TTS скрипта: {YANDEX_SCRIPT}")
    py = VENV_PYTHON if VENV_PYTHON.is_file() else Path(sys.executable)
    subdir = workdir / f"part_{part.index:02d}"
    subdir.mkdir(parents=True, exist_ok=True)
    text_path = subdir / f"{stem}_part_{part.index:02d}.txt"
    text_path.write_text(part.text, encoding="utf-8")
    output = workdir / f"{stem}_part_{part.index:02d}.mp3"
    cmd = [
        str(py),
        str(YANDEX_SCRIPT),
        str(text_path),
        "-o",
        str(output),
        "--voice",
        YANDEX_VOICE,
        "--speed",
        YANDEX_SPEED,
        "--resume",
    ]
    env = os.environ.copy()
    proc = subprocess.run(
        cmd,
        check=False,
        cwd=str(ROOT / "scripts"),
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-800:]
        raise RuntimeError(f"yandex-tts failed: {err}")
    if not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError(f"yandex-tts не создал MP3: {output}")
    return output


def render_part_silero(part: BookPart, workdir: Path, stem: str) -> Path:
    """Озвучка части через Silero TTS (ударения `+` нативно)."""
    if not SILERO_SCRIPT.is_file():
        raise RuntimeError(f"Нет silero TTS скрипта: {SILERO_SCRIPT}")
    py = VENV_PYTHON if VENV_PYTHON.is_file() else Path(sys.executable)
    subdir = workdir / f"part_{part.index:02d}"
    subdir.mkdir(parents=True, exist_ok=True)
    text_path = subdir / f"{stem}_part_{part.index:02d}.txt"
    text_path.write_text(part.text, encoding="utf-8")
    output = workdir / f"{stem}_part_{part.index:02d}.mp3"
    cmd = [
        str(py),
        str(SILERO_SCRIPT),
        str(text_path),
        "-o",
        str(output),
        "--prepared",
        "--resume",
        "--speaker",
        SILERO_SPEAKER,
    ]
    env = os.environ.copy()
    env["PDF_AUDIO_TEXT_PREPARED"] = "1"
    proc = subprocess.run(
        cmd,
        check=False,
        cwd=str(ROOT / "scripts"),
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-800:]
        raise RuntimeError(f"silero-tts failed: {err}")
    if not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError(f"silero-tts не создал MP3: {output}")
    return output


def _split_by_chapters(cleaned_text: str) -> list[tuple[str, str]]:
    """Разбить по заголовкам глав, если их ≥ 2. Иначе один блок."""
    lines = cleaned_text.splitlines()
    heads: list[int] = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s:
            continue
        if CHAPTER_SPLIT.match(s) or (s.startswith("#") and len(s) > 2):
            heads.append(i)
    if len(heads) < 2:
        return [("Текст", cleaned_text)]

    sections: list[tuple[str, str]] = []
    for n, start in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        block_lines = lines[start:end]
        heading = block_lines[0].strip().lstrip("#").strip() or f"Глава {n + 1}"
        body = "\n".join(block_lines).strip()
        if len(body) >= 80:
            sections.append((heading[:100], body + "\n"))
    return sections or [("Текст", cleaned_text)]


def split_into_book_parts(title: str, cleaned_text: str) -> list[BookPart]:
    """Главы (если есть) → при необходимости дорезаем до PART_TARGET_CHARS."""
    sections = _split_by_chapters(cleaned_text)
    pieces: list[tuple[str, str]] = []
    for heading, body in sections:
        chunks = split_text(body, PART_TARGET_CHARS)
        if len(chunks) == 1:
            pieces.append((heading, chunks[0]))
        else:
            for i, chunk in enumerate(chunks, start=1):
                pieces.append((f"{heading}. Часть {i}", chunk))

    total = len(pieces)
    parts: list[BookPart] = []
    for index, (heading, text) in enumerate(pieces, start=1):
        if total == 1:
            part_title = title
        else:
            part_title = f"{title}. {heading}. Файл {index} из {total}."
        parts.append(BookPart(index=index, title=part_title, text=text))
    return parts


def pcm_to_wav(pcm: bytes, path: Path, sample_rate: int = 24000) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


def save_audio_blob(data: bytes, mime: str, path: Path) -> None:
    if mime in ("audio/L16", "audio/pcm", "audio/raw"):
        pcm_to_wav(data, path)
        return
    if mime in ("audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3"):
        path.write_bytes(data)
        return
    if data[:4] == b"RIFF":
        path.write_bytes(data)
        return
    pcm_to_wav(data, path)


def synth_chunk(client, text: str) -> tuple[bytes, str]:
    from google.genai import types

    response = client.models.generate_content(
        model=GEMINI_TTS_MODEL,
        contents=PROMPT_PREFIX + text,
        config=types.GenerateContentConfig(
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                language_code="ru-RU",
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=GEMINI_TTS_VOICE
                    )
                ),
            ),
        ),
    )
    part = response.candidates[0].content.parts[0]
    raw = part.inline_data.data
    data = raw if isinstance(raw, (bytes, bytearray)) else base64.b64decode(raw)
    return data, part.inline_data.mime_type


def chunk_ok(path: Path) -> bool:
    return path.is_file() and path.stat().st_size >= MIN_AUDIO_BYTES


def concat_audio(parts: list[Path], output_mp3: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        list_path = Path(f.name)
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")
    tmp_mp3 = output_mp3.with_suffix(".tmp.mp3")
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
        tmp_mp3.replace(output_mp3)
    finally:
        list_path.unlink(missing_ok=True)
        tmp_mp3.unlink(missing_ok=True)


def render_part_gemini(client, part: BookPart, workdir: Path, stem: str) -> Path:
    subdir = workdir / f"part_{part.index:02d}"
    subdir.mkdir(parents=True, exist_ok=True)
    text_path = subdir / f"{stem}_part_{part.index:02d}.txt"
    text_path.write_text(part.text, encoding="utf-8")

    chunks = split_text(part.text, CHUNK_MAX_CHARS)
    audio_parts: list[Path] = []
    for idx, chunk in enumerate(chunks, start=1):
        wav_path = subdir / f"chunk_{idx:04d}.wav"
        if wav_path.is_file() and chunk_ok(wav_path):
            audio_parts.append(wav_path)
            continue
        ok = False
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                data, mime = synth_chunk(client, chunk)
                save_audio_blob(data, mime, wav_path)
                if chunk_ok(wav_path):
                    ok = True
                    break
            except Exception:
                logging.exception("TTS chunk failed attempt=%s chunk=%s", attempt, idx)
                time.sleep(2 * attempt)
        if not ok:
            raise RuntimeError(f"Не удалось озвучить кусок {idx} в части {part.index}")
        audio_parts.append(wav_path)
        time.sleep(0.5)

    output = workdir / f"{stem}_part_{part.index:02d}.mp3"
    concat_audio(audio_parts, output)
    return output


def render_part_edge(part: BookPart, workdir: Path, stem: str) -> Path:
    """Озвучка части через проверенный scripts/docx_to_mp3_edge.py."""
    if not EDGE_SCRIPT.is_file():
        raise RuntimeError(f"Нет edge TTS скрипта: {EDGE_SCRIPT}")
    py = VENV_PYTHON if VENV_PYTHON.is_file() else Path(sys.executable)
    subdir = workdir / f"part_{part.index:02d}"
    subdir.mkdir(parents=True, exist_ok=True)
    text_path = subdir / f"{stem}_part_{part.index:02d}.txt"
    text_path.write_text(part.text, encoding="utf-8")
    output = workdir / f"{stem}_part_{part.index:02d}.mp3"
    cmd = [
        str(py),
        str(EDGE_SCRIPT),
        str(text_path),
        "-o",
        str(output),
        "--skip-preflight",
        "--prepared",
        "--workers",
        "4",
        "--voice",
        EDGE_VOICE,
        f"--rate={EDGE_RATE}",
    ]
    env = os.environ.copy()
    # Текст уже prepare_for_tts (+ silero → U+0301). Не гонять второй раз.
    env["PDF_AUDIO_TEXT_PREPARED"] = "1"
    env["PDF_AUDIO_RUACCENT"] = "0"
    env["PDF_AUDIO_STRESS"] = "0"
    try:
        subprocess.run(
            cmd,
            check=True,
            cwd=str(ROOT / "scripts"),
            capture_output=True,
            text=True,
            env=env,
        )
    except subprocess.CalledProcessError:
        cmd = [
            str(py),
            str(EDGE_SCRIPT),
            str(text_path),
            "-o",
            str(output),
            "--skip-preflight",
            "--prepared",
            "--workers",
            "4",
            "--voice",
            EDGE_VOICE,
            f"--rate={EDGE_RATE}",
        ]
        proc = subprocess.run(
            cmd, check=False, cwd=str(ROOT / "scripts"), capture_output=True, text=True, env=env
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "")[-800:]
            raise RuntimeError(f"edge-tts failed: {err}")
    if not output.is_file() or output.stat().st_size < 1000:
        raise RuntimeError(f"edge-tts не создал MP3: {output}")
    return output


def _gemini_client():
    from google import genai

    if not GEMINI_API_KEY:
        raise RuntimeError("Не задан GEMINI_API_KEY")
    return genai.Client(api_key=GEMINI_API_KEY)


def _render_one_part(part: BookPart, workdir: Path, stem: str, provider: str) -> Path:
    output = workdir / f"{stem}_part_{part.index:02d}.mp3"
    if output.is_file() and output.stat().st_size >= 1000:
        logging.info("resume skip existing %s", output.name)
        return output
    if provider == "gemini":
        return render_part_gemini(_gemini_client(), part, workdir, stem)
    if provider == "silero":
        return render_part_silero(part, workdir, stem)
    if provider == "yandex":
        return render_part_yandex(part, workdir, stem)
    return render_part_edge(part, workdir, stem)


def convert_book_to_mp3s(
    source_path: Path,
    workdir: Path,
    *,
    progress_cb=None,
    resume: bool = True,
) -> tuple[str, list[Path], int]:
    """Аудиокнига: pdf/txt/md/docx → список MP3-частей.

    progress_cb(done_idx, total, part_title, mp3_path | None, stage)
      stage: prepare|part_start|part_done|done
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("Не найден ffmpeg")
    if not source_path.is_file():
        raise RuntimeError(f"Нет файла: {source_path}")

    title, raw = load_source_text(source_path)
    if progress_cb:
        progress_cb(0, 0, title, None, "prepare")
    cleaned = clean_for_tts(raw)
    if len(cleaned.strip()) < 40:
        raise RuntimeError(
            "Почти нет текста после очистки. Для PDF нужен текстовый слой (не скан)."
        )
    parts = split_into_book_parts(title, cleaned)
    stem = slugify(title)
    (workdir / f"{stem}.raw.txt").write_text(raw, encoding="utf-8")
    (workdir / f"{stem}.tts.txt").write_text(cleaned, encoding="utf-8")
    (workdir / f"{stem}.parts.json").write_text(
        __import__("json").dumps(
            [{"index": p.index, "title": p.title, "chars": len(p.text)} for p in parts],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    provider = TTS_PROVIDER
    if provider == "auto":
        provider = "edge"  # для длинных книг edge надёжнее
    if provider == "gemini" and not GEMINI_API_KEY:
        raise RuntimeError("Не задан GEMINI_API_KEY")

    outputs: list[Path] = []
    total = len(parts)
    for part in parts:
        if progress_cb:
            progress_cb(part.index - 1, total, part.title, None, "part_start")
        try:
            mp3 = _render_one_part(part, workdir, stem, provider if provider != "auto" else "edge")
        except Exception as exc:
            if provider == "gemini":
                logging.warning("gemini part failed, edge fallback: %s", exc)
                mp3 = _render_one_part(part, workdir, stem, "edge")
            else:
                raise
        # Если часть слишком тяжёлая для Telegram — предупреждаем в лог (редко при 32k chars)
        if mp3.stat().st_size > PART_MAX_MP3_BYTES:
            logging.warning(
                "part %s is large: %.1f MB", part.index, mp3.stat().st_size / 1024 / 1024
            )
        outputs.append(mp3)
        if progress_cb:
            progress_cb(part.index, total, part.title, mp3, "part_done")

    if progress_cb:
        progress_cb(total, total, title, None, "done")
    logging.info("book TTS ok parts=%s chars=%s provider=%s", len(outputs), len(cleaned), provider)
    return title, outputs, len(cleaned)


def convert_pdf_to_mp3s(pdf_path: Path, workdir: Path) -> tuple[str, list[Path], int]:
    """Обратная совместимость: то же, что convert_book_to_mp3s."""
    return convert_book_to_mp3s(pdf_path, workdir)


async def _standalone_main() -> None:
    """Опциональный отдельный запуск этого файла как бота."""
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import Command, CommandStart
    from aiogram.types import FSInputFile, Message

    if not TELEGRAM_TOKEN:
        raise RuntimeError("Set PDF_AUDIO_BOT_TOKEN or TELEGRAM_TOKEN in .env")
    if not ADMIN_ID:
        raise RuntimeError("Set ADMIN_ID in .env")

    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()
    lock = asyncio.Lock()
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    def _allowed(message: Message) -> bool:
        return bool(ADMIN_ID and message.from_user and message.from_user.id == ADMIN_ID)

    @dp.message(CommandStart())
    @dp.message(Command("help"))
    async def _help(message: Message) -> None:
        if not _allowed(message):
            await message.answer("Бот закрыт.")
            return
        await message.answer(
            "Пришли PDF документом. Верну MP3. Длинные книги — несколькими частями."
        )

    @dp.message(F.document)
    async def _doc(message: Message) -> None:
        if not _allowed(message):
            await message.answer("Нет доступа.")
            return
        document = message.document
        if not document or not (document.file_name or "").lower().endswith(".pdf"):
            await message.answer("Нужен PDF.")
            return
        async with lock:
            status = await message.answer("Скачиваю и озвучиваю…")
            workdir = MEDIA_ROOT / f"{message.chat.id}_{message.message_id}_{int(time.time())}"
            workdir.mkdir(parents=True, exist_ok=True)
            pdf_path = workdir / (document.file_name or "input.pdf")
            try:
                await bot.download(document, destination=pdf_path)
                title, mp3_paths, total_chars = await asyncio.to_thread(
                    convert_pdf_to_mp3s, pdf_path, workdir
                )
                await status.edit_text(f"Готово: {title[:120]} ({total_chars} симв.)")
                for idx, mp3_path in enumerate(mp3_paths, start=1):
                    cap = title if len(mp3_paths) == 1 else f"{title}\nЧасть {idx}/{len(mp3_paths)}"
                    await message.answer_audio(
                        audio=FSInputFile(mp3_path),
                        title=mp3_path.stem[:64],
                        caption=cap[:1024],
                    )
            except Exception as exc:
                logging.exception("standalone pdf fail")
                await status.edit_text(f"Ошибка: {exc}")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(_standalone_main())
