"""P0-брак контента: фейковые цифры, псевдонаука, типичный ИИ-мусор."""

from __future__ import annotations

import re

# Фразы — всегда P0 (все персоны, кроме явных цитат в lenin curated).
_P0_PHRASES = (
    "85%",
    "исследования показали",
    "учёные доказали",
    "ученые доказали",
    "scientists proved",
    "studies show that",
    "кортизол −",
    "кортизол -20",
    "снижают кортизол",
    "датчики показывают",
    "раскрой свой потенциал",
    "железная дисциплина",
    "слушай, кириллыч",
    "кириллыч, слушай",
)

# Проценты рядом с «травм/риск/улучш» без источника — P0.
_PCT_HYPE_RE = re.compile(
    r"\d{1,3}\s*%\s*(?:\s*(?:травм|риск|случаев|улучш|сниж|повыш|эффектив))",
    re.IGNORECASE,
)
_PCT_ANY_RE = re.compile(r"\b\d{1,3}\s*%")

_STERN_EXTRA = (
    "turkish get-up",
    "туркис",
    "гиревой спорт",
    "wksf",
    "200 повторений",
)


def p0_findings(text: str, persona_key: str | None = None) -> list[str]:
    """Список причин P0-брака. Непустой = не публиковать."""
    if not text or text.startswith("🛑"):
        return []
    findings: list[str] = []
    low = text.lower()

    for ph in _P0_PHRASES:
        if ph.lower() in low:
            findings.append(f"P0: запрещённая фраза «{ph}»")

    if _PCT_HYPE_RE.search(text):
        findings.append("P0: выдуманный процент (травмы/риск/эффект)")

    if persona_key in ("stern", "gdepar", None):
        if "mcgill" in low and _PCT_ANY_RE.search(text):
            findings.append("P0: McGill + проценты без источника")
        if persona_key == "stern":
            for ph in _STERN_EXTRA:
                if ph in low:
                    findings.append(f"P0: stern — «{ph}»")

    if persona_key == "gdepar":
        if re.search(r"\d{2,3}\s*°\s*c", low) or re.search(r"\d{2,3}\s*градус", low):
            if "печ" in low or "парил" in low or "жар" in low:
                findings.append("P0: выдуманная температура в парилке")

    # Дедуп по тексту
    seen: set[str] = set()
    out: list[str] = []
    for f in findings:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out
