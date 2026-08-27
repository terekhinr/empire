#!/usr/bin/env python3
"""TXT → audiobook (wav/mp3) via local Silero TTS on CUDA.

Example:
  python scripts/tts_generator.py book.txt output.mp3 --speaker aidar
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import numpy as np
import torch
from num2words import num2words
from pydub import AudioSegment
from ruaccent import RUAccent
from tqdm import tqdm

LOGGER = logging.getLogger("tts_generator")

# Silero v4_ru: aidar, baya, kseniya, xenia, eugene
DEFAULT_SPEAKER = "aidar"
DEFAULT_SAMPLE_RATE = 24000
DEFAULT_MAX_CHUNK = 800
SILERO_REPO = "snakers4/silero-models"


class AudiobookGenerator:
    """Local Silero TTS audiobook pipeline (CUDA by default, CPU via device='cpu')."""

    def __init__(
        self,
        *,
        speaker: str = DEFAULT_SPEAKER,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        max_chunk_chars: int = DEFAULT_MAX_CHUNK,
        custom_dict: dict[str, str] | None = None,
        device: str | None = None,
    ) -> None:
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cpu":
                LOGGER.warning("CUDA недоступна — работаем на CPU (медленно)")
        elif str(device).startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError(f"Запрошен {device}, но torch.cuda.is_available() == False")
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA недоступна. Укажите --device cpu или поставьте torch+CUDA."
            )

        self.speaker = speaker
        self.sample_rate = int(sample_rate)
        self.max_chunk_chars = int(max_chunk_chars)
        self.custom_dict = {k.lower(): v for k, v in (custom_dict or {}).items()}
        self.device = torch.device(device)

        LOGGER.info("Loading Silero TTS v4_ru on %s …", self.device)
        self.model, _example = torch.hub.load(
            repo_or_dir=SILERO_REPO,
            model="silero_tts",
            language="ru",
            speaker="v4_ru",
            trust_repo=True,
        )
        self.model.to(self.device)
        # Silero hub wrapper may not be a torch.nn.Module with .eval()
        if hasattr(self.model, "eval"):
            self.model.eval()

        LOGGER.info("Loading accent engine …")
        self._accentizer: RUAccent | None = None
        self._silero_accentor = None
        try:
            self._accentizer = RUAccent()
            self._accentizer.load(
                omograph_model_size="turbo",
                use_dictionary=True,
                tiny_mode=True,
            )
            # smoke-test (some onnx builds miss token_type_ids)
            _ = self._accentizer.process_all("проверка")
            LOGGER.info("Accent engine: RUAccent turbo")
        except Exception:
            LOGGER.exception("RUAccent unavailable — falling back to silero-stress")
            self._accentizer = None
            from silero_stress import load_accentor

            self._silero_accentor = load_accentor()
            LOGGER.info("Accent engine: silero-stress")
        if self._accentizer is None and self._silero_accentor is None:
            raise RuntimeError("Не удалось загрузить ни RUAccent, ни silero-stress")

        LOGGER.info(
            "Ready: speaker=%s sample_rate=%s max_chunk=%s",
            self.speaker,
            self.sample_rate,
            self.max_chunk_chars,
        )

    def normalize_text(self, text: str) -> str:
        """Numbers → Russian words; strip risky symbols; dashes → pause commas."""
        text = text.replace("\u00a0", " ")
        text = text.replace("—", ", ").replace("–", ", ").replace("−", ", ")
        text = text.replace("…", "...")

        def _num_repl(match: re.Match[str]) -> str:
            raw = match.group(0)
            try:
                if "." in raw or "," in raw:
                    value = float(raw.replace(",", "."))
                    return num2words(value, lang="ru")
                return num2words(int(raw), lang="ru")
            except Exception:
                LOGGER.warning("num2words failed for %r — leave as-is", raw)
                return raw

        # integers / decimals (avoid years glued to letters)
        text = re.sub(r"(?<![A-Za-zА-Яа-яЁё])\d+(?:[.,]\d+)?(?![A-Za-zА-Яа-яЁё])", _num_repl, text)

        # drop characters that often break Silero; keep punctuation useful for pauses
        text = re.sub(r"[^\w\s.,!?;:\-«»\"'()+ёЁА-Яа-яA-Za-z]", " ", text, flags=re.UNICODE)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def apply_accents(self, text: str) -> str:
        """Place Silero `+` stress marks via RUAccent + optional custom_dict."""
        if not text.strip():
            return text

        # User overrides first (plain → already-stressed forms with +).
        for src, dst in self.custom_dict.items():
            pattern = re.compile(rf"(?i)\b{re.escape(src)}\b")
            text = pattern.sub(dst, text)

        try:
            if self._accentizer is not None:
                stressed = self._accentizer.process_all(text)
            else:
                assert self._silero_accentor is not None
                # silero-stress is happier on shorter paragraphs
                parts: list[str] = []
                for para in re.split(r"(\n\s*\n)", text):
                    if not para.strip() or para.isspace() or re.fullmatch(r"\n\s*\n", para):
                        parts.append(para)
                        continue
                    if len(para) <= 1000:
                        parts.append(self._silero_accentor(para))
                    else:
                        for sent in re.split(r"(?<=[.!?…])\s+", para):
                            if sent:
                                parts.append(self._silero_accentor(sent))
                stressed = " ".join(p for p in parts if p is not None)
        except Exception:
            LOGGER.exception("Accentizer failed — returning text without new accents")
            return text

        # Re-apply custom_dict after accentizer (omographs / preferred forms).
        for src, dst in self.custom_dict.items():
            # Match both plain and accentizer output of the same word (no +).
            plain = re.sub(r"\+", "", src)
            pattern = re.compile(rf"(?i)\b{re.escape(plain)}\b|\b{re.escape(src)}\b")
            stressed = pattern.sub(dst, stressed)
            # Also replace accentizer's + form of the same letters ignoring +.
            stressed = self._replace_word_ignoring_plus(stressed, plain, dst)

        return stressed

    @staticmethod
    def _replace_word_ignoring_plus(text: str, plain_word: str, replacement: str) -> str:
        """Replace a word even if RUAccent inserted `+` inside it."""
        letters = re.escape(plain_word)
        # п+окерное ↔ покерное
        parts = list(letters)
        flex = r"\+?".join(parts)
        return re.sub(rf"(?i)\b{flex}\b", replacement, text)

    def chunk_text(self, text: str) -> list[str]:
        """Split into ≤ max_chunk_chars pieces by sentences, then commas."""
        text = text.strip()
        if not text:
            return []

        sentences = self._split_sentences(text)
        chunks: list[str] = []
        buf = ""

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(sent) > self.max_chunk_chars:
                if buf:
                    chunks.append(buf.strip())
                    buf = ""
                chunks.extend(self._split_long_sentence(sent))
                continue

            candidate = f"{buf} {sent}".strip() if buf else sent
            if len(candidate) <= self.max_chunk_chars:
                buf = candidate
            else:
                if buf:
                    chunks.append(buf.strip())
                buf = sent

        if buf:
            chunks.append(buf.strip())
        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        # Prefer NLTK if installed; otherwise regex.
        try:
            import nltk
            from nltk.tokenize.punkt import PunktSentenceTokenizer

            try:
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                nltk.download("punkt", quiet=True)
            try:
                nltk.data.find("tokenizers/punkt_tab")
            except LookupError:
                try:
                    nltk.download("punkt_tab", quiet=True)
                except Exception:
                    pass
            tokenizer = PunktSentenceTokenizer()
            return [s.strip() for s in tokenizer.tokenize(text) if s.strip()]
        except Exception:
            parts = re.split(r"(?<=[.!?…])\s+", text)
            return [p.strip() for p in parts if p.strip()]

    def _split_long_sentence(self, sentence: str) -> list[str]:
        pieces = re.split(r"(?<=[,;:])\s+", sentence)
        out: list[str] = []
        buf = ""
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            cand = f"{buf} {piece}".strip() if buf else piece
            if len(cand) <= self.max_chunk_chars:
                buf = cand
                continue
            if buf:
                out.append(buf)
            if len(piece) <= self.max_chunk_chars:
                buf = piece
            else:
                # hard wrap as last resort
                for i in range(0, len(piece), self.max_chunk_chars):
                    out.append(piece[i : i + self.max_chunk_chars])
                buf = ""
        if buf:
            out.append(buf)
        return out

    def _synth_chunk(self, chunk: str) -> torch.Tensor | None:
        try:
            # Silero accepts +stress; empty / latin-only often raises ValueError.
            if not re.search(r"[А-Яа-яЁё]", chunk):
                LOGGER.warning("Skip non-Cyrillic chunk: %r", chunk[:80])
                return None
            with torch.inference_mode():
                audio = self.model.apply_tts(
                    text=chunk,
                    speaker=self.speaker,
                    sample_rate=self.sample_rate,
                )
            if not isinstance(audio, torch.Tensor):
                audio = torch.as_tensor(audio)
            return audio.detach().float().cpu()
        except Exception:
            LOGGER.exception("TTS failed for chunk (%s chars): %r", len(chunk), chunk[:120])
            return None

    def generate_text(
        self,
        text: str,
        output_file: str | Path,
        *,
        prepared: bool = False,
    ) -> Path:
        """Normalize/accent (unless prepared) → chunk → TTS → wav/mp3."""
        out_path = Path(output_file)
        if prepared:
            stressed = text
            LOGGER.info("Using pre-stressed text (%s chars)", len(stressed))
        else:
            normalized = self.normalize_text(text)
            stressed = self.apply_accents(normalized)
        chunks = self.chunk_text(stressed)
        LOGGER.info("Chunks: %s", len(chunks))
        if not chunks:
            raise RuntimeError("После нормализации текст пуст")

        gap = torch.zeros(int(self.sample_rate * 0.12), dtype=torch.float32)
        audio_parts: list[torch.Tensor] = []
        failed = 0

        for chunk in tqdm(chunks, desc="Silero TTS", unit="chunk"):
            tensor = self._synth_chunk(chunk)
            if tensor is None:
                failed += 1
                continue
            if audio_parts:
                audio_parts.append(gap)
            audio_parts.append(tensor)

        if not audio_parts:
            raise RuntimeError("Все чанки провалились — аудио не собрано")

        waveform = torch.cat(audio_parts, dim=0).numpy()
        peak = float(np.max(np.abs(waveform))) if waveform.size else 0.0
        if peak > 1e-6:
            waveform = waveform / peak * 0.89

        pcm16 = (waveform * 32767.0).astype(np.int16)
        segment = AudioSegment(
            pcm16.tobytes(),
            frame_rate=self.sample_rate,
            sample_width=2,
            channels=1,
        )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = out_path.suffix.lower()
        if suffix == ".wav":
            segment.export(out_path, format="wav")
        elif suffix == ".mp3":
            segment.export(out_path, format="mp3", bitrate="192k")
        else:
            raise ValueError("output_file должен заканчиваться на .wav или .mp3")

        LOGGER.info(
            "Done: %s (%.1f s audio, failed_chunks=%s)",
            out_path,
            len(segment) / 1000.0,
            failed,
        )
        return out_path

    def generate(
        self,
        input_file: str,
        output_file: str,
        *,
        prepared: bool = False,
    ) -> Path:
        """Read .txt → (optional) normalize/accents → chunk → TTS → wav/mp3."""
        in_path = Path(input_file)
        if not in_path.is_file():
            raise FileNotFoundError(f"Нет входного файла: {in_path}")
        raw = in_path.read_text(encoding="utf-8")
        LOGGER.info("Read %s (%s chars)", in_path, len(raw))
        return self.generate_text(raw, output_file, prepared=prepared)


def _load_custom_dict(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    if not path.is_file():
        raise FileNotFoundError(f"custom dict not found: {path}")
    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        src, _, dst = line.partition("=")
        src, dst = src.strip(), dst.strip()
        if src and dst:
            mapping[src] = dst
    return mapping


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="TXT → audiobook via Silero TTS (CUDA/CPU)")
    p.add_argument("input_file", type=str, help="Исходный .txt")
    p.add_argument("output_file", type=str, help="Выходной .wav или .mp3")
    p.add_argument("--speaker", default=DEFAULT_SPEAKER, help="aidar|baya|kseniya|xenia|eugene")
    p.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    p.add_argument("--max-chunk", type=int, default=DEFAULT_MAX_CHUNK)
    p.add_argument(
        "--device",
        default=None,
        help="cuda | cpu (по умолчанию: cuda если есть, иначе cpu)",
    )
    p.add_argument(
        "--prepared",
        action="store_true",
        help="Текст уже с ударениями (+); не гонять normalize/accent снова",
    )
    p.add_argument(
        "--custom-dict",
        type=Path,
        default=None,
        help="Файл исключений: слово=форм+а (по строке)",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        gen = AudiobookGenerator(
            speaker=args.speaker,
            sample_rate=args.sample_rate,
            max_chunk_chars=args.max_chunk,
            custom_dict=_load_custom_dict(args.custom_dict),
            device=args.device,
        )
        gen.generate(args.input_file, args.output_file, prepared=args.prepared)
        return 0
    except Exception:
        LOGGER.exception("Fatal error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
