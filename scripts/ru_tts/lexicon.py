"""JSON-словарь исключений (самообучение QA-цикла)."""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from .models import LexiconEntry, MarkupKind

LOGGER = logging.getLogger("ru_tts.lexicon")


class ExceptionLexicon:
    """Потокобезопасный JSON-lexicon для автопополнения из Whisper QA."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._by_key: dict[str, LexiconEntry] = {}
        self.load()

    @staticmethod
    def _key(surface: str, context_left: str | None) -> str:
        ctx = (context_left or "").casefold()
        return f"{surface.casefold()}|{ctx}"

    def load(self) -> None:
        with self._lock:
            self._by_key.clear()
            if not self.path.is_file():
                return
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            items = raw if isinstance(raw, list) else raw.get("entries", [])
            for item in items:
                entry = LexiconEntry.from_dict(item)
                self._by_key[self._key(entry.surface, entry.context_left)] = entry
            LOGGER.info("lexicon loaded path=%s entries=%s", self.path, len(self._by_key))

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "entries": [e.to_dict() for e in sorted(self._by_key.values(), key=lambda x: x.surface)],
            }
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)

    def get(self, surface: str, context_left: str | None = None) -> LexiconEntry | None:
        with self._lock:
            return self._by_key.get(self._key(surface, context_left)) or self._by_key.get(
                self._key(surface, None)
            )

    def upsert(
        self,
        surface: str,
        replacement: str,
        *,
        kind: MarkupKind = MarkupKind.ALIAS,
        context_left: str | None = None,
        cer: float | None = None,
        notes: str = "",
    ) -> LexiconEntry:
        with self._lock:
            key = self._key(surface, context_left)
            existing = self._by_key.get(key)
            if existing:
                existing.replacement = replacement
                existing.kind = kind
                existing.hits += 1
                existing.last_cer = cer
                if notes:
                    existing.notes = notes
                entry = existing
            else:
                entry = LexiconEntry(
                    surface=surface,
                    replacement=replacement,
                    kind=kind,
                    context_left=context_left,
                    hits=1,
                    last_cer=cer,
                    notes=notes,
                )
                self._by_key[key] = entry
            self.save()
            LOGGER.warning(
                "lexicon upsert surface=%r replacement=%r kind=%s cer=%s",
                surface,
                replacement,
                kind.value,
                cer,
            )
            return entry

    def entries(self) -> list[LexiconEntry]:
        with self._lock:
            return list(self._by_key.values())
