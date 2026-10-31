"""WhisperValidator: TTS → ASR → CER → lexicon → сигнал на переозвучку."""
from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .lexicon import ExceptionLexicon
from .models import LexiconEntry, MarkupKind, TokenDiff, ValidationResult

LOGGER = logging.getLogger("ru_tts.whisper")

# Известные фонетические путаницы RU TTS: (ref, hyp) → IPA.
_PHONEME_CONFUSIONS: dict[tuple[str, str], str] = {
    ("много", "мново"): "ˈmnogə",
    ("немного", "немново"): "nʲɪˈmnogə",
}

# Normalize hyp/ref for token compare
_NON_WORD = re.compile(r"[^a-zа-яё0-9]+", re.I)


@dataclass(slots=True)
class WhisperConfig:
    model_size: str = "large-v3"  # или turbo / medium / small
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "ru"
    beam_size: int = 1
    vad_filter: bool = True
    max_cer: float = 0.12
    max_retries: int = 2


class WhisperValidator:
    """Петля обратной связи: сгенерированный MP3 ↔ эталонный текст.

    Workflow:
      1. transcribe(mp3) через faster-whisper
      2. CER(ref, hyp)
      3. если CER > max_cer → align tokens, найти bad tokens
      4. предложить LexiconEntry (alias / phoneme / stress)
      5. upsert в ExceptionLexicon
      6. вернуть ValidationResult(ok=False) → pipeline переозвучивает чанк
    """

    def __init__(
        self,
        lexicon: ExceptionLexicon,
        *,
        config: WhisperConfig | None = None,
        suggest_fix: Callable[[str, str], LexiconEntry | None] | None = None,
    ) -> None:
        self.lexicon = lexicon
        self.config = config or WhisperConfig()
        self._suggest_fix = suggest_fix or default_suggest_fix
        self._model = None

    # -------------------------------------------------------------- model I/O

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper не установлен. pip install faster-whisper"
            ) from exc
        LOGGER.info(
            "loading whisper model=%s device=%s compute=%s",
            self.config.model_size,
            self.config.device,
            self.config.compute_type,
        )
        self._model = WhisperModel(
            self.config.model_size,
            device=self.config.device,
            compute_type=self.config.compute_type,
        )
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        model = self._ensure_model()
        segments, _info = model.transcribe(
            str(audio_path),
            language=self.config.language,
            beam_size=self.config.beam_size,
            vad_filter=self.config.vad_filter,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        LOGGER.info("whisper transcript path=%s chars=%s", audio_path.name, len(text))
        return text

    async def transcribe_async(self, audio_path: Path) -> str:
        return await asyncio.to_thread(self.transcribe, audio_path)

    # ------------------------------------------------------------------- CER

    @staticmethod
    def normalize_for_cer(text: str) -> str:
        t = unicodedata.normalize("NFC", text).casefold().replace("ё", "е")
        t = _NON_WORD.sub("", t)
        return t

    @staticmethod
    def levenshtein(a: str, b: str) -> int:
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(
                    min(
                        cur[j - 1] + 1,
                        prev[j] + 1,
                        prev[j - 1] + (ca != cb),
                    )
                )
            prev = cur
        return prev[-1]

    def char_error_rate(self, reference: str, hypothesis: str) -> float:
        r = self.normalize_for_cer(reference)
        h = self.normalize_for_cer(hypothesis)
        if not r:
            return 0.0 if not h else 1.0
        return self.levenshtein(r, h) / len(r)

    # ----------------------------------------------------------- token align

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", text.casefold().replace("ё", "е"))

    def align_bad_tokens(self, reference: str, hypothesis: str) -> list[TokenDiff]:
        """Простой word-level alignment (Needleman–Wunsch light / greedy LCS diffs)."""
        ref_toks = self.tokenize(reference)
        hyp_toks = self.tokenize(hypothesis)
        # DP edit script
        n, m = len(ref_toks), len(hyp_toks)
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            dp[i][0] = i
        for j in range(1, m + 1):
            dp[0][j] = j
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = 0 if ref_toks[i - 1] == hyp_toks[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + cost,
                )
        bad: list[TokenDiff] = []
        i, j = n, m
        while i > 0 or j > 0:
            if i > 0 and j > 0 and ref_toks[i - 1] == hyp_toks[j - 1] and dp[i][j] == dp[i - 1][j - 1]:
                i -= 1
                j -= 1
            elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
                bad.append(
                    TokenDiff(
                        ref=ref_toks[i - 1],
                        hyp=hyp_toks[j - 1],
                        ref_index=i - 1,
                        hyp_index=j - 1,
                    )
                )
                i -= 1
                j -= 1
            elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                bad.append(
                    TokenDiff(ref=ref_toks[i - 1], hyp="", ref_index=i - 1, hyp_index=max(j - 1, 0))
                )
                i -= 1
            else:
                bad.append(
                    TokenDiff(ref="", hyp=hyp_toks[j - 1], ref_index=max(i - 1, 0), hyp_index=j - 1)
                )
                j -= 1
        bad.reverse()
        # только замены/искажения с непустым ref
        return [d for d in bad if d.ref and d.ref != d.hyp]

    # -------------------------------------------------------------- validate

    def validate(
        self,
        audio_path: Path,
        reference_text: str,
        *,
        auto_lexicon: bool = True,
    ) -> ValidationResult:
        hyp = self.transcribe(audio_path)
        cer = self.char_error_rate(reference_text, hyp)
        bad = self.align_bad_tokens(reference_text, hyp)
        ok = cer <= self.config.max_cer
        updates: list[LexiconEntry] = []

        if ok:
            LOGGER.info("chunk OK cer=%.3f path=%s", cer, audio_path.name)
            return ValidationResult(
                ok=True,
                cer=cer,
                reference=reference_text,
                hypothesis=hyp,
                bad_tokens=bad,
                message=f"CER {cer:.3f} <= {self.config.max_cer}",
            )

        LOGGER.warning(
            "chunk FAIL cer=%.3f threshold=%.3f path=%s bad_tokens=%s hyp=%r",
            cer,
            self.config.max_cer,
            audio_path.name,
            [(b.ref, b.hyp) for b in bad[:8]],
            hyp[:160],
        )

        if auto_lexicon:
            ref_toks = self.tokenize(reference_text)
            for diff in bad:
                entry = self._suggest_fix(diff.ref, diff.hyp)
                if entry is None:
                    continue
                # левый контекст для омографов
                ctx = None
                if 0 < diff.ref_index < len(ref_toks):
                    ctx = ref_toks[diff.ref_index - 1]
                saved = self.lexicon.upsert(
                    entry.surface,
                    entry.replacement,
                    kind=entry.kind,
                    context_left=entry.context_left or ctx,
                    cer=cer,
                    notes=entry.notes or f"auto from hyp={diff.hyp!r}",
                )
                updates.append(saved)

        return ValidationResult(
            ok=False,
            cer=cer,
            reference=reference_text,
            hypothesis=hyp,
            bad_tokens=bad,
            lexicon_updates=updates,
            message=f"CER {cer:.3f} > {self.config.max_cer}; lexicon+={len(updates)}",
        )

    async def validate_async(
        self,
        audio_path: Path,
        reference_text: str,
        *,
        auto_lexicon: bool = True,
    ) -> ValidationResult:
        return await asyncio.to_thread(
            self.validate, audio_path, reference_text, auto_lexicon=auto_lexicon
        )

    async def validate_with_retries(
        self,
        *,
        reference_plain: str,
        synth_fn,  # async (ssml: str, out: Path) -> Path
        preprocess_fn,  # () -> PreprocessResult  (пересчёт после lexicon)
        out_path: Path,
    ) -> ValidationResult:
        """Полный QA-цикл: synth → validate → (lexicon) → re-synth до max_retries."""
        last: ValidationResult | None = None
        for attempt in range(1, self.config.max_retries + 2):
            prepared = preprocess_fn()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            audio = await synth_fn(prepared.ssml, out_path)
            last = await self.validate_async(audio, prepared.plain, auto_lexicon=True)
            last.message = f"attempt={attempt}; " + last.message
            if last.ok:
                return last
            LOGGER.warning("re-synth scheduled attempt=%s cer=%.3f", attempt, last.cer)
        assert last is not None
        return last


# ------------------------------------------------------------------ suggest

_STRESS_HINTS: dict[str, str] = {
    "дорого": "до́рого",
    "замок": "замо́к",  # default lock; castle needs context
    "мука": "мука́",
    "стороны": "стороны́",
    "стоит": "сто́ит",
}


def default_suggest_fix(ref: str, hyp: str) -> LexiconEntry | None:
    """Эвристика: известные путаницы → phoneme/stress/alias."""
    ref_n = ref.casefold().replace("ё", "е")
    hyp_n = hyp.casefold().replace("ё", "е")
    if not ref_n:
        return None

    # фонемы: много→мново
    ipa = _PHONEME_CONFUSIONS.get((ref_n, hyp_n))
    if ipa:
        return LexiconEntry(
            surface=ref_n,
            replacement=ipa,
            kind=MarkupKind.PHONEME,
            notes=f"phoneme confusion {hyp_n!r}",
        )

    # stress dictionary
    if ref_n in _STRESS_HINTS and ref_n != hyp_n:
        spoken = _STRESS_HINTS[ref_n]
        return LexiconEntry(
            surface=ref_n,
            replacement=spoken,
            kind=MarkupKind.ALIAS,
            notes=f"stress hint; hyp={hyp_n!r}",
        )

    # неизвестные пары не пишем в lexicon автоматически — только WARNING в validate()
    return None
