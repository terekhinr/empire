"""RuTtsPipeline — оркестратор: preprocess → chunk → synth → Whisper QA → merge."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from .audio_merger import AudioMerger
from .lexicon import ExceptionLexicon
from .models import ChunkJob
from .preprocessor import TextPreprocessor
from .tts_client import TTSClient, build_tts_client
from .whisper_validator import WhisperConfig, WhisperValidator

LOGGER = logging.getLogger("ru_tts.pipeline")


class RuTtsPipeline:
    """Полный цикл RU Text → Speech с самообучением.

    Пример::

        pipe = RuTtsPipeline(workdir=Path("tmp/ru_tts"), enable_qa=True)
        mp3 = await pipe.run("Много людей со стороны банка…", Path("out.mp3"))
    """

    def __init__(
        self,
        *,
        workdir: Path,
        client: TTSClient | None = None,
        lexicon_path: Path | None = None,
        enable_qa: bool = True,
        max_chunk_chars: int = 1800,
        whisper: WhisperConfig | None = None,
    ) -> None:
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.client = client or build_tts_client()
        lex_path = lexicon_path or (workdir / "exception_lexicon.json")
        self.lexicon = ExceptionLexicon(lex_path)
        self.preprocessor = TextPreprocessor(
            lexicon=self.lexicon,
            use_ssml=self.client.supports_ssml or True,
        )
        self.validator = WhisperValidator(self.lexicon, config=whisper or WhisperConfig())
        self.merger = AudioMerger()
        self.enable_qa = enable_qa
        self.max_chunk_chars = max_chunk_chars

    def chunk_text(self, text: str) -> list[str]:
        """Нарезка по абзацам/предложениям без разрыва SSML-тегов (грубо по plain)."""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[str] = []
        buf = ""
        for para in paragraphs:
            cand = f"{buf}\n\n{para}".strip() if buf else para
            if len(cand) <= self.max_chunk_chars:
                buf = cand
                continue
            if buf:
                chunks.append(buf)
            if len(para) <= self.max_chunk_chars:
                buf = para
                continue
            sentences = re.split(r"(?<=[.!?…])\s+", para)
            buf = ""
            for sent in sentences:
                cand = f"{buf} {sent}".strip() if buf else sent
                if len(cand) <= self.max_chunk_chars:
                    buf = cand
                else:
                    if buf:
                        chunks.append(buf)
                    buf = sent
            if buf:
                chunks.append(buf)
                buf = ""
        if buf:
            chunks.append(buf)
        return chunks or [text]

    async def run(self, text: str, output: Path) -> Path:
        parts = self.chunk_text(text)
        LOGGER.info(
            "pipeline start provider=%s chunks=%s qa=%s",
            self.client.name,
            len(parts),
            self.enable_qa,
        )
        audio_parts: list[Path] = []
        for i, part in enumerate(parts, 1):
            job = await self._process_chunk(i, part)
            if job.audio_path is None:
                raise RuntimeError(f"chunk {i}: нет аудио")
            audio_parts.append(job.audio_path)
        return self.merger.merge(audio_parts, output)

    async def _process_chunk(self, index: int, source: str) -> ChunkJob:
        chunk_dir = self.workdir / f"chunk_{index:04d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        out_mp3 = chunk_dir / "audio.mp3"
        job = ChunkJob(index=index, source_text=source, ssml="")

        def _prep():
            return self.preprocessor.process(source)

        if not self.enable_qa:
            prepared = _prep()
            job.ssml = prepared.ssml
            job.audio_path = await self.client.synthesize(prepared.ssml, out_mp3)
            LOGGER.info("chunk %s synthesized (qa off)", index)
            return job

        async def _synth(ssml: str, path: Path) -> Path:
            return await self.client.synthesize(ssml, path)

        result = await self.validator.validate_with_retries(
            reference_plain=source,
            synth_fn=_synth,
            preprocess_fn=_prep,
            out_path=out_mp3,
        )
        job.ssml = _prep().ssml
        job.audio_path = out_mp3
        job.attempts = self.validator.config.max_retries + 1
        job.meta["cer"] = result.cer
        job.meta["ok"] = result.ok
        job.meta["hypothesis"] = result.hypothesis
        if result.ok:
            LOGGER.info("chunk %s OK cer=%.3f", index, result.cer)
        else:
            LOGGER.warning(
                "chunk %s accepted with cer=%.3f after retries hyp=%r",
                index,
                result.cer,
                result.hypothesis[:120],
            )
        return job
