"""Удаление PII перед отправкой в LLM (ТЗ §4.4 AI Insights)."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE = re.compile(r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")
_TG_USER = re.compile(r"@[a-zA-Z0-9_]{4,32}")


def strip_pii(text: str) -> str:
    if not text:
        return ""
    out = _EMAIL.sub("[email]", text)
    out = _PHONE.sub("[phone]", out)
    out = _TG_USER.sub("[user]", out)
    return out


def validate_payload_for_llm(payload: dict) -> dict:
    """Рекурсивно очищает строки в dict для внешнего LLM."""
    if isinstance(payload, dict):
        return {k: validate_payload_for_llm(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [validate_payload_for_llm(x) for x in payload]
    if isinstance(payload, str):
        return strip_pii(payload)
    return payload
