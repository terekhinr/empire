"""RU Text → Speech pipeline (v2).

Модули:
  TextPreprocessor  — морфология, NBSP-склейка, SSML-паузы, омографы
  TTSClient         — абстракция Yandex v3 / ElevenLabs / OpenAI
  WhisperValidator  — TTS→ASR→CER→lexicon→re-synth
  AudioMerger       — склейка чанков в MP3
  RuTtsPipeline     — оркестратор

Старый путь (`prepare_md_for_tts`, `tts_pronunciation_dict.txt`) остаётся
рабочим; этот пакет — целевая архитектура без ручных `+` / `[[ipa]]` в тексте.
"""
from __future__ import annotations

from .audio_merger import AudioMerger
from .models import ChunkJob, LexiconEntry, ValidationResult
from .pipeline import RuTtsPipeline
from .preprocessor import TextPreprocessor
from .tts_client import ElevenLabsClient, OpenAITTSClient, TTSClient, YandexSpeechKitV3Client
from .whisper_validator import WhisperValidator

__all__ = [
    "AudioMerger",
    "ChunkJob",
    "ElevenLabsClient",
    "LexiconEntry",
    "OpenAITTSClient",
    "RuTtsPipeline",
    "TTSClient",
    "TextPreprocessor",
    "ValidationResult",
    "WhisperValidator",
    "YandexSpeechKitV3Client",
]
