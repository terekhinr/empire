"""TextPreprocessor: морфология, NBSP-склейка, омографы, SSML-паузы."""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from .lexicon import ExceptionLexicon
from .models import LexiconEntry, MarkupKind

LOGGER = logging.getLogger("ru_tts.preprocessor")

_WORD_CHARS = r"A-Za-zА-Яа-яЁё0-9"
_TOKEN_RE = re.compile(rf"([{_WORD_CHARS}]+(?:-[{_WORD_CHARS}]+)*)|(\s+)|([^\s{_WORD_CHARS}])")

# Короткие клитики: после них — NBSP, чтобы TTS не делал микропаузу и не глотал.
_CLITICS = frozenset(
    {
        "в",
        "во",
        "на",
        "к",
        "ко",
        "с",
        "со",
        "у",
        "о",
        "об",
        "обо",
        "от",
        "до",
        "по",
        "за",
        "из",
        "изо",
        "без",
        "безо",
        "для",
        "при",
        "про",
        "через",
        "не",
        "ни",
        "же",
        "ли",
        "бы",
        "б",
        "а",
        "и",
        "но",
        "да",
        "то",
        "ну",
    }
)

# Известные фонетические баги SpeechKit → IPA (подставляем в SSML phoneme).
_DEFAULT_PHONEME_FIXES: dict[str, str] = {
    "много": "ˈmnogə",
    "немного": "nʲɪˈmnogə",
}

_NBSP = "\xa0"


@dataclass(frozen=True, slots=True)
class PreprocessResult:
    plain: str  # текст без SSML (для CER / Whisper ref)
    ssml: str  # <speak>…</speak>
    applied_lexicon: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def _morph():
    try:
        import pymorphy3

        return pymorphy3.MorphAnalyzer()
    except Exception:
        try:
            import pymorphy2

            return pymorphy2.MorphAnalyzer()
        except Exception:
            LOGGER.warning("pymorphy unavailable — homograph morph rules degraded")
            return None


class TextPreprocessor:
    """Интеллектуальный препроцессинг RU → SSML.

    Порядок:
      1. light clean (NFC, пробелы)
      2. lexicon exceptions (из QA-цикла / ручные)
      3. омографы (правила + pymorphy POS/падеж)
      4. NBSP после клитик
      5. структурные паузы → SSML <break>
      6. опциональные phoneme-fixы (много→IPA)
    """

    def __init__(
        self,
        *,
        lexicon: ExceptionLexicon | None = None,
        phoneme_fixes: dict[str, str] | None = None,
        use_ssml: bool = True,
        paragraph_break_ms: int = 500,
        sentence_break_ms: int = 300,
        comma_break_ms: int = 150,
    ) -> None:
        self.lexicon = lexicon
        self.phoneme_fixes = dict(phoneme_fixes or _DEFAULT_PHONEME_FIXES)
        self.use_ssml = use_ssml
        self.paragraph_break_ms = paragraph_break_ms
        self.sentence_break_ms = sentence_break_ms
        self.comma_break_ms = comma_break_ms

    # ------------------------------------------------------------------ public

    def process(self, text: str) -> PreprocessResult:
        raw = self._light_clean(text)
        applied: list[str] = []
        body = self._apply_lexicon(raw, applied)
        body = self.disambiguate_homographs(body, skip_words={a.casefold() for a in applied})
        body = self.glue_clitics(body)
        plain = self._plain_from_glued(body)
        if self.use_ssml:
            ssml = self.to_ssml(body)
        else:
            ssml = plain
        LOGGER.info(
            "preprocess chars=%s lexicon_hits=%s ssml=%s",
            len(plain),
            len(applied),
            self.use_ssml,
        )
        return PreprocessResult(plain=plain, ssml=ssml, applied_lexicon=tuple(applied))

    # -------------------------------------------------------------- cleaning

    @staticmethod
    def _light_clean(text: str) -> str:
        text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
        text = text.replace("\u00ad", "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # ---------------------------------------------------------------- lexicon

    def _apply_lexicon(self, text: str, applied: list[str]) -> str:
        if not self.lexicon:
            return text
        # longest surface first
        entries = sorted(self.lexicon.entries(), key=lambda e: len(e.surface), reverse=True)
        for entry in entries:
            before = text
            text = self._apply_entry(text, entry)
            if text != before:
                applied.append(entry.surface)
        return text

    def _apply_entry(self, text: str, entry: LexiconEntry) -> str:
        surface = entry.surface
        if entry.context_left:
            pat = re.compile(
                rf"(?<![{_WORD_CHARS}])({re.escape(entry.context_left)})(\s+)({re.escape(surface)})(?![{_WORD_CHARS}])",
                re.IGNORECASE,
            )

            def _ctx(m: re.Match[str]) -> str:
                return m.group(1) + m.group(2) + self._wrap_replacement(entry)

            return pat.sub(_ctx, text)

        pat = re.compile(
            rf"(?<![{_WORD_CHARS}]){re.escape(surface)}(?![{_WORD_CHARS}])",
            re.IGNORECASE,
        )
        return pat.sub(lambda _m: self._wrap_replacement(entry), text)

    def _wrap_replacement(self, entry: LexiconEntry) -> str:
        if not self.use_ssml:
            return entry.replacement
        if entry.kind == MarkupKind.SSML:
            return entry.replacement
        if entry.kind == MarkupKind.PHONEME:
            ph = entry.replacement.strip()
            return f'<phoneme alphabet="ipa" ph="{_xml_escape_attr(ph)}">{_xml_escape(entry.surface)}</phoneme>'
        if entry.kind == MarkupKind.ALIAS:
            return (
                f'<sub alias="{_xml_escape_attr(entry.replacement)}">'
                f"{_xml_escape(entry.surface)}</sub>"
            )
        # stress: оставляем replacement как текст (адаптер TTS может понимать +)
        return _xml_escape(entry.replacement)

    # ------------------------------------------------------------- homographs

    def disambiguate_homographs(self, text: str, *, skip_words: set[str] | None = None) -> str:
        """Контекстное разрешение топ-омографов.

        Результат — текст с SSML <sub> (если use_ssml) или plain stress-маркерами.
        """
        text = self._fix_storony(text)
        text = self._fix_zamok(text)
        text = self._fix_stoit(text)
        text = self._fix_muka(text)
        text = self._fix_phoneme_defaults(text, skip_words=skip_words)
        return text

    def _sub_alias(self, surface: str, spoken: str) -> str:
        if self.use_ssml:
            return f'<sub alias="{_xml_escape_attr(spoken)}">{_xml_escape(surface)}</sub>'
        return spoken

    def _fix_storony(self, text: str) -> str:
        # им.п. мн.: две/обе/три/четыре/все стороны → стОроны
        text = re.sub(
            rf"(?<![{_WORD_CHARS}])((?:две|обе|три|четыре|все|эти|те)\s+)(стороны)(?![{_WORD_CHARS}])",
            lambda m: m.group(1) + self._sub_alias(m.group(2), "сто́роны"),
            text,
            flags=re.IGNORECASE,
        )
        # род.п.: со/с … стороны → сторонЫ
        text = re.sub(
            rf"(?<![{_WORD_CHARS}])((?:со|с)(?:\s+\S+){{0,2}}\s+)(стороны)(?![{_WORD_CHARS}])",
            lambda m: m.group(1) + self._sub_alias(m.group(2), "стороны́"),
            text,
            flags=re.IGNORECASE,
        )
        morph = _morph()
        if morph is None:
            return text

        def _morph_storony(m: re.Match[str]) -> str:
            left, word = m.group(1), m.group(2)
            parses = morph.parse(word)
            if any("gent" in p.tag for p in parses[:3]):
                return left + self._sub_alias(word, "стороны́")
            return m.group(0)

        return re.sub(
            rf"(?<![{_WORD_CHARS}])((?:со|с)\s+)(стороны)(?![{_WORD_CHARS}])",
            _morph_storony,
            text,
            flags=re.IGNORECASE,
        )

    def _fix_zamok(self, text: str) -> str:
        lock_prev = r"на|под|за|ключ|дверной|навесной|кодовый|электронный"
        castle_prev = r"старинный|средневековый|королевский|рыцарский"
        text = re.sub(
            rf"(?<![{_WORD_CHARS}])((?:{lock_prev})\s+)(замок)(?![{_WORD_CHARS}])",
            lambda m: m.group(1) + self._sub_alias(m.group(2), "замо́к"),
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            rf"(?<![{_WORD_CHARS}])((?:{castle_prev})\s+)(замок)(?![{_WORD_CHARS}])",
            lambda m: m.group(1) + self._sub_alias(m.group(2), "за́мок"),
            text,
            flags=re.IGNORECASE,
        )
        return text

    def _fix_stoit(self, text: str) -> str:
        # цена: сколько стоит → сто́ит; положение: стоит у окна → стои́т
        text = re.sub(
            rf"(?<![{_WORD_CHARS}])((?:сколько|столько|дорого|дёшево|дешево|это)\s+)(стоит)(?![{_WORD_CHARS}])",
            lambda m: m.group(1) + self._sub_alias(m.group(2), "сто́ит"),
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            rf"(?<![{_WORD_CHARS}])(стоит)(\s+(?:на|у|в|возле|около|посреди|перед|за)\b)",
            lambda m: self._sub_alias(m.group(1), "стои́т") + m.group(2),
            text,
            flags=re.IGNORECASE,
        )
        return text

    def _fix_muka(self, text: str) -> str:
        text = re.sub(
            rf"(?<![{_WORD_CHARS}])((?:пшеничная|ржаная|коробка|мешок|килограмм)\s+)(мука|муки)(?![{_WORD_CHARS}])",
            lambda m: m.group(1) + self._sub_alias(m.group(2), "мука́" if m.group(2).lower() == "мука" else "муки́"),
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            rf"(?<![{_WORD_CHARS}])((?:тяжёлая|тяжелая|душевная|моральная)\s+)(мука)(?![{_WORD_CHARS}])",
            lambda m: m.group(1) + self._sub_alias(m.group(2), "му́ка"),
            text,
            flags=re.IGNORECASE,
        )
        return text

    def _fix_phoneme_defaults(self, text: str, *, skip_words: set[str] | None = None) -> str:
        if not self.use_ssml:
            return text
        skip = skip_words or set()
        for word, ipa in sorted(self.phoneme_fixes.items(), key=lambda x: -len(x[0])):
            if word.casefold() in skip:
                continue
            pat = re.compile(
                rf"(?<![{_WORD_CHARS}])({re.escape(word)})(?![{_WORD_CHARS}])",
                re.IGNORECASE,
            )

            def _ph(m: re.Match[str], ipa: str = ipa) -> str:
                surface = m.group(1)
                return (
                    f'<phoneme alphabet="ipa" ph="{_xml_escape_attr(ipa)}">'
                    f"{_xml_escape(surface)}</phoneme>"
                )

            text = pat.sub(_ph, text)
        return text

    # ----------------------------------------------------------- NBSP glue

    def glue_clitics(self, text: str) -> str:
        """Пробел после коротких предлогов/частиц → NBSP.

        Не трогает уже размеченный SSML (теги пропускаем целиком).
        """
        parts: list[str] = []
        i = 0
        while i < len(text):
            if text[i] == "<":
                j = text.find(">", i)
                if j == -1:
                    parts.append(text[i:])
                    break
                parts.append(text[i : j + 1])
                i = j + 1
                continue
            m = re.match(rf"([{_WORD_CHARS}]+)", text[i:])
            if m:
                word = m.group(1)
                parts.append(word)
                i += len(word)
                if word.casefold() in _CLITICS:
                    # следующий пробельный пролёт → один NBSP
                    sp = re.match(r"[ \t]+", text[i:])
                    if sp:
                        parts.append(_NBSP)
                        i += len(sp.group(0))
                continue
            parts.append(text[i])
            i += 1
        return "".join(parts)

    @staticmethod
    def _plain_from_glued(text: str) -> str:
        """Убрать SSML-теги, NBSP→space — эталон для Whisper CER."""
        plain = re.sub(r"<[^>]+>", "", text)
        plain = plain.replace(_NBSP, " ")
        plain = re.sub(r"\s+", " ", plain)
        return plain.strip()

    # ----------------------------------------------------------------- SSML

    def to_ssml(self, body: str) -> str:
        """Обернуть тело в <speak> и вставить <break> по пунктуации/абзацам.

        Уже присутствующие SSML-теги (sub/phoneme) сохраняются.
        """
        # абзацы
        paragraphs = re.split(r"\n\s*\n", body)
        rendered: list[str] = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para = self._breaks_in_paragraph(para)
            rendered.append(para)
        join = f' <break time="{self.paragraph_break_ms}ms"/> '.join(rendered)
        return f"<speak>{join}</speak>"

    def _breaks_in_paragraph(self, para: str) -> str:
        # конец предложения
        para = re.sub(
            r"([.!?…])(\s+)",
            rf'\1 <break time="{self.sentence_break_ms}ms"/> ',
            para,
        )
        # запятая / точка с запятой — короче
        para = re.sub(
            r"([,;:])(\s+)",
            rf'\1 <break time="{self.comma_break_ms}ms"/> ',
            para,
        )
        # длинное тире как пауза
        para = re.sub(
            r"\s+[—–]\s+",
            f' <break time="{self.comma_break_ms}ms"/> ',
            para,
        )
        return para.replace("\n", " ")


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _xml_escape_attr(s: str) -> str:
    return _xml_escape(s).replace("'", "&apos;")
