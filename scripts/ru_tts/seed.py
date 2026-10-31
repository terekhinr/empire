"""Первичный seed exception_lexicon из известных багов SpeechKit."""
from __future__ import annotations

from pathlib import Path

from .lexicon import ExceptionLexicon
from .models import MarkupKind

# Проверенные фонетические/ударные фиксы (из legacy tts_pronunciation_dict).
_SEED: list[tuple[str, str, MarkupKind, str]] = [
    ("много", "ˈmnogə", MarkupKind.PHONEME, "legacy: мново"),
    ("немного", "nʲɪˈmnogə", MarkupKind.PHONEME, "legacy: немново"),
    # Yandex v1 лучше ест +ударение, чем акут в alias
    ("дорого", "д+орого", MarkupKind.ALIAS, "legacy: дорово"),
    ("нищепанк", "нищеп+анк", MarkupKind.ALIAS, "legacy stress"),
]


def seed_lexicon(path: Path, *, force: bool = False) -> ExceptionLexicon:
    lex = ExceptionLexicon(path)
    if lex.entries() and not force:
        return lex
    for surface, repl, kind, notes in _SEED:
        if lex.get(surface) and not force:
            continue
        lex.upsert(surface, repl, kind=kind, notes=notes)
    return lex
