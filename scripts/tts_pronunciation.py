"""Pronunciation lexicon + legal-form expansion for Russian TTS.

Yandex SpeechKit has no hosted PLS; we emulate it in text before synthesize:
  - alias / stress / phoneme
  - context: орган [after:звук|музыка] = +орган
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")
_WORD_CHARS = r"A-Za-zА-Яа-яЁё"

DEFAULT_DICT_PATH = Path(__file__).resolve().parent / "tts_pronunciation_dict.txt"

_CTX_KEY = re.compile(
    r"^(?P<word>.+?)\s*\[after:(?P<after>[^\]]+)\]\s*$",
    re.I,
)


@dataclass(frozen=True)
class LexRule:
    word: str
    replacement: str
    after: tuple[str, ...] = ()

    @property
    def is_phoneme(self) -> bool:
        return self.replacement.strip().startswith("[[")


def expand_legal_forms(text: str) -> str:
    """Юрформы и гео-АО до синтеза (анти-«аоаоао» у SpeechKit)."""
    geo: list[tuple[str, str]] = [
        (
            r"(?i)\bХанты-Мансийск\w*\s+АО\s*[—\-–]?\s*Югра\b",
            "Ханты-Мансийский автономный округ — Югра",
        ),
        (r"(?i)\bЕврейск\w*\s+АО\b", "Еврейская автономная область"),
        (
            r"(?i)\b((?:Ямало-)?Ненецк\w*|Ханты-Мансийск\w*|Чукотск\w*)\s+АО\b",
            r"\1 автономный округ",
        ),
    ]
    for pat, rep in geo:
        text = re.sub(pat, rep, text)

    legal: list[tuple[str, str]] = [
        (r"(?i)\bООО\b", "общество с ограниченной ответственностью"),
        (r"(?i)\bПАО\b", "публичное акционерное общество"),
        (r"(?i)\bЗАО\b", "закрытое акционерное общество"),
        (r"(?i)\bОАО\b", "открытое акционерное общество"),
        (r"(?i)\bАО\b", "акционерное общество"),
        (r"(?i)\bИП\b", "индивидуальный предприниматель"),
    ]
    for pat, rep in legal:
        text = re.sub(pat, rep, text)
    return text


def _flexible_body(word: str) -> str:
    parts: list[str] = []
    for ch in word:
        if ch.isspace():
            parts.append(r"\s+")
        elif ch in _VOWELS:
            parts.append(r"\+?" + re.escape(ch) + r"\u0301?")
        else:
            parts.append(r"\+?" + re.escape(ch))
    return "".join(parts)


def _token_pattern(word: str) -> re.Pattern[str]:
    body = _flexible_body(word)
    return re.compile(
        rf"(?<![{_WORD_CHARS}]){body}(?![{_WORD_CHARS}])",
        re.IGNORECASE,
    )


def load_pronunciation_rules(path: Path | None = None) -> list[LexRule]:
    if path is None:
        env = (os.getenv("PDF_AUDIO_PRONUNCIATION_DICT") or "").strip()
        path = Path(env) if env else DEFAULT_DICT_PATH
    if not path.is_file():
        return []
    rules: list[LexRule] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        src, _, dst = line.partition("=")
        src, dst = src.strip(), dst.strip()
        if not src or not dst:
            continue
        m = _CTX_KEY.match(src)
        if m:
            word = m.group("word").strip().casefold()
            after = tuple(
                a.strip().casefold() for a in m.group("after").split("|") if a.strip()
            )
            rules.append(LexRule(word=word, replacement=dst, after=after))
        else:
            rules.append(LexRule(word=src.casefold(), replacement=dst, after=()))
    return rules


def load_pronunciation_dict(path: Path | None = None) -> dict[str, str]:
    """Плоский dict без [after:] — для CER / обратной совместимости."""
    return {r.word: r.replacement for r in load_pronunciation_rules(path) if not r.after}


@lru_cache(maxsize=1)
def _cached_rules() -> tuple[LexRule, ...]:
    return tuple(load_pronunciation_rules(None))


def clear_pronunciation_cache() -> None:
    _cached_rules.cache_clear()


def _phonemes_enabled() -> bool:
    flag = (os.getenv("PDF_AUDIO_PHONEMES") or "").strip().lower()
    if flag in ("1", "true", "yes", "on", "yandex"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    prov = (os.getenv("PDF_AUDIO_TTS_PROVIDER") or "").strip().lower()
    return prov == "yandex"


def _apply_context_rule(text: str, rule: LexRule) -> str:
    """prev ∈ after + word → prev + replacement (prev орфография сохраняется)."""
    for prev in sorted(rule.after, key=len, reverse=True):
        pat = re.compile(
            rf"(?<![{_WORD_CHARS}])({_flexible_body(prev)})(\s+)({_flexible_body(rule.word)})(?![{_WORD_CHARS}])",
            re.IGNORECASE,
        )
        text = pat.sub(rf"\1\2{rule.replacement}", text)
    return text


def apply_pronunciation_lexicon(
    text: str,
    mapping: dict[str, str] | None = None,
    *,
    allow_phonemes: bool | None = None,
    rules: list[LexRule] | None = None,
) -> str:
    """Contextual [after:] first, then flat longest-first."""
    if allow_phonemes is None:
        allow_phonemes = _phonemes_enabled()

    if rules is None and mapping is not None:
        rules = [LexRule(word=k, replacement=v) for k, v in mapping.items()]
    elif rules is None:
        rules = list(_cached_rules())

    if not rules:
        return text

    ctx = sorted(
        (r for r in rules if r.after),
        key=lambda r: (len(r.word), max((len(a) for a in r.after), default=0)),
        reverse=True,
    )
    for rule in ctx:
        if rule.is_phoneme and not allow_phonemes:
            continue
        text = _apply_context_rule(text, rule)

    flat = sorted((r for r in rules if not r.after), key=lambda r: len(r.word), reverse=True)
    for rule in flat:
        if rule.is_phoneme and not allow_phonemes:
            continue
        text = _token_pattern(rule.word).sub(rule.replacement, text)
    return text


def pronunciation_dict_path() -> Path:
    env = (os.getenv("PDF_AUDIO_PRONUNCIATION_DICT") or "").strip()
    return Path(env) if env else DEFAULT_DICT_PATH
