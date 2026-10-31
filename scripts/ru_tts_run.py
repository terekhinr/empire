#!/usr/bin/env python3
"""CLI: RU TTS v2 — текст/md → mp3 (preprocess + Yandex + optional Whisper QA).

  python3 scripts/ru_tts_run.py input.md -o out.mp3
  PDF_AUDIO_QA=1 python3 scripts/ru_tts_run.py sample.txt -o out.mp3
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = val.strip().strip('"').strip("'")


_load_dotenv()

from ru_tts.pipeline import RuTtsPipeline  # noqa: E402
from ru_tts.seed import seed_lexicon  # noqa: E402
from ru_tts.tts_client import YandexSpeechKitV3Client, build_tts_client  # noqa: E402
from ru_tts.whisper_validator import WhisperConfig  # noqa: E402


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _light_clean(raw: str) -> str:
    import re

    from prepare_md_for_tts import expand_speech_abbreviations, prepare_md_for_tts
    from tts_nsw import expand_nsw

    text = prepare_md_for_tts(raw)
    text = re.sub(r"\s*sil<\[\d+\]>", "", text)
    text = expand_speech_abbreviations(text)
    text = expand_nsw(text)
    return text.strip() + "\n"


async def _amain() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    p = argparse.ArgumentParser(description="RU TTS pipeline v2")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument("--workdir", type=Path, default=None)
    p.add_argument("--qa", action="store_true", default=None)
    p.add_argument("--no-qa", action="store_true")
    p.add_argument("--provider", default=None)
    p.add_argument("--whisper-model", default=os.getenv("PDF_AUDIO_WHISPER_MODEL", "small"))
    args = p.parse_args()

    if not args.input.is_file():
        print(f"нет файла: {args.input}", file=sys.stderr)
        return 1

    raw = args.input.read_text(encoding="utf-8")
    text = _light_clean(raw)
    workdir = args.workdir or (args.output.parent / f".{args.output.stem}_ru_tts")
    lexicon = ROOT / "data" / "ru_tts_exception_lexicon.json"
    seed_lexicon(lexicon)

    qa = _env_bool("PDF_AUDIO_QA", False)
    if args.qa:
        qa = True
    if args.no_qa:
        qa = False

    provider = args.provider or os.getenv("RU_TTS_PROVIDER") or "yandex"
    if provider in ("yandex", "yandex_v3", "speechkit"):
        voice = os.getenv("PDF_AUDIO_YANDEX_VOICE", "filipp")
        speed = float(os.getenv("PDF_AUDIO_YANDEX_SPEED", "0.95"))
        client = YandexSpeechKitV3Client(voice=voice, speed=speed)
    else:
        client = build_tts_client(provider)

    pipe = RuTtsPipeline(
        workdir=workdir,
        client=client,
        lexicon_path=lexicon,
        enable_qa=qa,
        whisper=WhisperConfig(
            model_size=args.whisper_model,
            max_cer=float(os.getenv("PDF_AUDIO_MAX_CER", "0.15")),
            max_retries=int(os.getenv("PDF_AUDIO_QA_RETRIES", "2")),
        ),
    )
    out = await pipe.run(text, args.output)
    print(f"OK {out} ({out.stat().st_size} bytes) qa={qa} provider={client.name}")
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
