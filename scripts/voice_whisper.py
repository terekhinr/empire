"""Shared faster-whisper settings for voice pipeline (VPS and diagnostics)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

DEFAULT_INITIAL_PROMPT = (
    "Заметки для книги, дневник, голосовая запись на русском языке. "
    "Имена: Алекс, Виталик, Серёга, дядя Фёдор, Трупик майора, пенсия."
)

_VOICE_ENV_LOADED = False


def _load_voice_env() -> None:
    global _VOICE_ENV_LOADED
    if _VOICE_ENV_LOADED:
        return
    env_file = os.environ.get("VOICE_ENV_FILE", "/etc/empire/voice.env")
    path = Path(env_file)
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)
    _VOICE_ENV_LOADED = True


def whisper_settings() -> dict[str, str | int | float | bool]:
    _load_voice_env()
    return {
        "model": os.environ.get("VOICE_WHISPER_MODEL", "small"),
        "device": os.environ.get("VOICE_WHISPER_DEVICE", "cpu"),
        "compute_type": os.environ.get("VOICE_WHISPER_COMPUTE_TYPE", ""),
        "beam_size": int(os.environ.get("VOICE_WHISPER_BEAM_SIZE", "5")),
        "best_of": int(os.environ.get("VOICE_WHISPER_BEST_OF", "5")),
        "temperature": float(os.environ.get("VOICE_WHISPER_TEMPERATURE", "0")),
        "initial_prompt": os.environ.get("VOICE_WHISPER_INITIAL_PROMPT", DEFAULT_INITIAL_PROMPT),
        "vad_filter": os.environ.get("VOICE_WHISPER_VAD", "1") not in ("0", "false", "no"),
        "preprocess": os.environ.get("VOICE_AUDIO_PREPROCESS", "1") not in ("0", "false", "no"),
    }


def resolve_compute_type(device: str, explicit: str) -> str:
    if explicit:
        return explicit
    if device == "cuda":
        return "float16"
    # int8_float16 is not available on all CPU builds; int8 is the safe default.
    return "int8"


def audio_probe(audio: Path) -> dict[str, str]:
    if not shutil.which("ffprobe"):
        return {}
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,bit_rate:stream=codec_name,sample_rate,channels",
                "-of",
                "default=noprint_wrappers=1",
                str(audio),
            ],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    info: dict[str, str] = {}
    for line in out.splitlines():
        if "=" in line:
            key, val = line.split("=", 1)
            info[key.strip()] = val.strip()
    return info


def preprocess_audio(audio: Path) -> tuple[Path, Path | None]:
    """Normalize to 16 kHz mono WAV — Whisper works better than phone m4a/mp3."""
    if os.environ.get("VOICE_AUDIO_PREPROCESS", "1") in ("0", "false", "no"):
        return audio, None
    if not shutil.which("ffmpeg"):
        return audio, None

    tmp = Path(tempfile.mkdtemp(prefix="voice-whisper-"))
    out = tmp / f"{audio.stem}.16k.wav"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(audio),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-af",
        "loudnorm",
        str(out),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        shutil.rmtree(tmp, ignore_errors=True)
        return audio, None
    if not out.is_file() or out.stat().st_size < 1000:
        shutil.rmtree(tmp, ignore_errors=True)
        return audio, None
    return out, tmp


def transcribe(
    audio: Path,
    *,
    model_size: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
) -> str:
    from faster_whisper import WhisperModel

    cfg = whisper_settings()
    model_size = model_size or str(cfg["model"])
    device = device or str(cfg["device"])
    compute_type = resolve_compute_type(device, compute_type or str(cfg["compute_type"]))

    src, tmp_dir = preprocess_audio(audio)
    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        segments, info = model.transcribe(
            str(src),
            language="ru",
            beam_size=int(cfg["beam_size"]),
            best_of=int(cfg["best_of"]),
            temperature=float(cfg["temperature"]),
            initial_prompt=str(cfg["initial_prompt"]),
            vad_filter=bool(cfg["vad_filter"]),
            vad_parameters={
                "min_silence_duration_ms": 400,
                "speech_pad_ms": 200,
            },
            condition_on_previous_text=True,
            word_timestamps=False,
        )
        text = "\n".join(s.text.strip() for s in segments if s.text.strip())
        print(
            f"  whisper: model={model_size} device={device} "
            f"compute={compute_type} lang={getattr(info, 'language', '?')} "
            f"prepped={src != audio}",
            flush=True,
        )
        return text
    finally:
        if tmp_dir is not None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
