"""Контекстное разрешение омографов для TTS (P3).

Работает ПОСЛЕ silero-stress и поверх него: ставит эталонный `+`.
Без обязательных зависимостей; pymorphy3 — опционально для проверки падежа.

Топ-омографы: стороны́/сто́роны, замо́к/за́мок, сто́ит/стои́т.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache

_WORD = r"A-Za-zА-Яа-яЁё"
_STRESS_STRIP = re.compile(r"[+\u0301]")


def _strip_stress(s: str) -> str:
    return _STRESS_STRIP.sub("", s)


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
            return None


def _flex(word: str) -> str:
    """Тело слова с опциональными +/́ (как в lexicon)."""
    vowels = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")
    parts: list[str] = []
    for ch in word:
        if ch in vowels:
            parts.append(r"\+?" + re.escape(ch) + r"\u0301?")
        else:
            parts.append(r"\+?" + re.escape(ch))
    return "".join(parts)


def _sub_word(text: str, word: str, repl: str) -> str:
    pat = re.compile(
        rf"(?<![{_WORD}]){_flex(word)}(?![{_WORD}])",
        re.IGNORECASE,
    )
    return pat.sub(repl, text)


def _replace_match_group(text: str, pattern: str, group: int, repl: str) -> str:
    """Заменить только group в каждом match на repl (сохраняя остальное)."""
    rx = re.compile(pattern, re.IGNORECASE | re.UNICODE)

    def _r(m: re.Match[str]) -> str:
        return m.string[m.start() : m.start(group)] + repl + m.string[m.end(group) : m.end()]

    return rx.sub(_r, text)


def disambiguate_storony(text: str) -> str:
    """сто́роны (им.п. мн.) vs стороны́ (род.п. ед.)."""
    # им.п. мн.: две/обе/все/эти стороны
    text = _replace_match_group(
        text,
        rf"(?<![{_WORD}])((?:две|обе|три|четыре|все|эти|те|обеи)\s+)({_flex('стороны')})(?![{_WORD}])",
        2,
        "ст+ороны",
    )
    # род.п.: со стороны / с … стороны — если ещё не сторон+ы
    text = _replace_match_group(
        text,
        rf"(?<![{_WORD}])((?:со|с)\s+(?:\S+\s+){{0,2}})({_flex('стороны')})(?![{_WORD}])",
        2,
        "сторон+ы",
    )
    # morph: если слева предлог со/с и pymorphy видит gent — уже покрыто regex
    return text


def disambiguate_zamok(text: str) -> str:
    """замо́к (запор) vs за́мок (крепость)."""
    # запор
    for prev in (
        "на",
        "под",
        "за",
        "ключ",
        "дверной",
        "навесной",
        "кодовый",
        "электронный",
    ):
        text = _replace_match_group(
            text,
            rf"(?<![{_WORD}])({_flex(prev)}\s+)({_flex('замок')})(?![{_WORD}])",
            2,
            "зам+ок",
        )
    text = _replace_match_group(
        text,
        rf"(?<![{_WORD}])({_flex('ключ')}\s+от\s+)({_flex('замка')})(?![{_WORD}])",
        2,
        "замк+а",
    )
    # крепость
    for prev in (
        "старинный",
        "средневековый",
        "королевский",
        "рыцарский",
        "разрушенный",
        "феодальный",
    ):
        text = _replace_match_group(
            text,
            rf"(?<![{_WORD}])({_flex(prev)}\s+)({_flex('замок')})(?![{_WORD}])",
            2,
            "з+амок",
        )
    text = _replace_match_group(
        text,
        rf"(?<![{_WORD}])({_flex('замок')})(\s+(?:короля|королей|графа|на\s+скале|у\s+моря))",
        1,
        "з+амок",
    )
    return text


def disambiguate_stoit(text: str) -> str:
    """сто́ит (цена) vs стои́т (положение)."""
    text = _replace_match_group(
        text,
        rf"(?<![{_WORD}])((?:сколько|столько|дорого|дёшево|дешево|это)\s+)({_flex('стоит')})(?![{_WORD}])",
        2,
        "ст+оит",
    )
    text = _replace_match_group(
        text,
        rf"(?<![{_WORD}])({_flex('стоит')})(\s+(?:ли|того|своих))",
        1,
        "ст+оит",
    )
    text = _replace_match_group(
        text,
        rf"(?<![{_WORD}])((?:не)\s+)({_flex('стоит')})(?![{_WORD}])",
        2,
        "ст+оит",
    )
    # положение
    text = _replace_match_group(
        text,
        rf"(?<![{_WORD}])({_flex('стоит')})(\s+(?:на|у|в|возле|около|посреди|перед|за)\b)",
        1,
        "сто+ит",
    )
    text = _replace_match_group(
        text,
        rf"(?<![{_WORD}])((?:он|она|оно|дом|человек|машина|стол|шкаф)\s+)({_flex('стоит')})(?![{_WORD}])",
        2,
        "сто+ит",
    )
    return text


def disambiguate_muka(text: str) -> str:
    """му́ка (мучение) vs мука́ (продукт) — продукт чаще в быту/еда."""
    for prev in ("пшеничная", "ржаная", "высший", "сорт", "килограмм", "мешок", "сахарная"):
        text = _replace_match_group(
            text,
            rf"(?<![{_WORD}])({_flex(prev)}\s+)({_flex('мука')})(?![{_WORD}])",
            2,
            "мук+а",
        )
    for prev in ("тяжёлая", "тяжелая", "душевная", "лютая", "напрасная"):
        text = _replace_match_group(
            text,
            rf"(?<![{_WORD}])({_flex(prev)}\s+)({_flex('мука')})(?![{_WORD}])",
            2,
            "м+ука",
        )
    return text


def apply_homograph_disambiguation(text: str) -> str:
    """Главный вход P3. Env: PDF_AUDIO_DISAMBIG=0 чтобы выключить."""
    flag = (os.getenv("PDF_AUDIO_DISAMBIG") or "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return text
    text = disambiguate_storony(text)
    text = disambiguate_zamok(text)
    text = disambiguate_stoit(text)
    text = disambiguate_muka(text)
    # опционально: gent-check через pymorphy для «со стороны»
    morph = _morph()
    if morph is not None:
        text = _morph_refine_storony(text, morph)
    return text


def _morph_refine_storony(text: str, morph) -> str:
    """Если «стороны» после предлога и parse=gent — сторон+ы."""

    def repl(m: re.Match[str]) -> str:
        word = _strip_stress(m.group(2))
        parses = morph.parse(word)
        if any("gent" in str(p.tag) and "sing" in str(p.tag) for p in parses[:3]):
            return f"{m.group(1)}сторон+ы"
        if any("nomn" in str(p.tag) and "plur" in str(p.tag) for p in parses[:3]):
            # только если слева числительное/определитель уже обработан regex
            return m.group(0)
        return m.group(0)

    return re.sub(
        rf"(?<![{_WORD}])((?:со|с)\s+)({_flex('стороны')})(?![{_WORD}])",
        repl,
        text,
        flags=re.IGNORECASE,
    )
