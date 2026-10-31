"""Общие типы пайплайна RU TTS."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class MarkupKind(str, Enum):
    """Как хранить коррекцию в lexicon."""

    ALIAS = "alias"  # <sub alias="…">слово</sub> / текстовая замена
    STRESS = "stress"  # ударная форма (для движков с +) или SSML emphasis
    PHONEME = "phoneme"  # SSML <phoneme> / IPA
    SSML = "ssml"  # произвольный SSML-фрагмент вместо токена


@dataclass(slots=True)
class LexiconEntry:
    """Одна запись словаря исключений (JSON)."""

    surface: str
    replacement: str
    kind: MarkupKind = MarkupKind.ALIAS
    context_left: str | None = None  # опциональный левый контекст
    hits: int = 0
    last_cer: float | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "replacement": self.replacement,
            "kind": self.kind.value,
            "context_left": self.context_left,
            "hits": self.hits,
            "last_cer": self.last_cer,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LexiconEntry:
        return cls(
            surface=str(data["surface"]),
            replacement=str(data["replacement"]),
            kind=MarkupKind(str(data.get("kind") or "alias")),
            context_left=data.get("context_left"),
            hits=int(data.get("hits") or 0),
            last_cer=data.get("last_cer"),
            notes=str(data.get("notes") or ""),
        )


@dataclass(slots=True)
class ChunkJob:
    """Один кусок текста на синтез + QA."""

    index: int
    source_text: str
    ssml: str
    audio_path: Path | None = None
    attempts: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TokenDiff:
    """Подозрительный токен: ref vs hyp."""

    ref: str
    hyp: str
    ref_index: int
    hyp_index: int


@dataclass(slots=True)
class ValidationResult:
    """Итог WhisperValidator для чанка."""

    ok: bool
    cer: float
    reference: str
    hypothesis: str
    bad_tokens: list[TokenDiff] = field(default_factory=list)
    lexicon_updates: list[LexiconEntry] = field(default_factory=list)
    message: str = ""
