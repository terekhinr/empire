"""Общие правила ленты pension на сайте и в RSS.

Посты канала попадают на сайт через status=published в post_drafts.
Дубликаты (несколько republish одного текста) режем по нормализованному заголовку.
"""
from __future__ import annotations

import html
import re
from typing import Any, Iterable, TypeVar

T = TypeVar("T")

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def pension_title_from_html(text: str | None) -> str:
    raw = text or ""
    m = re.search(r"<b>(.*?)</b>", raw, flags=re.I | re.S)
    if m:
        plain = _TAG_RE.sub("", m.group(1))
    else:
        plain = _TAG_RE.sub("", raw)
    plain = html.unescape(plain)
    plain = _SPACE_RE.sub(" ", plain).strip()
    return plain


def pension_title_key(text: str | None) -> str:
    t = pension_title_from_html(text).lower()
    t = re.sub(r"[«»\"'`“”]", "", t)
    t = re.sub(r"[^\wа-яё\s-]", " ", t, flags=re.I)
    return _SPACE_RE.sub(" ", t).strip()[:120]


def dedupe_pension_posts(posts: Iterable[T], *, text_attr: str = "text_content") -> list[T]:
    """Оставляет один пост на заголовок (первый / более ранний в переданном порядке)."""
    seen: set[str] = set()
    out: list[T] = []
    for p in posts:
        text = getattr(p, text_attr, None) if not isinstance(p, dict) else p.get(text_attr)
        key = pension_title_key(text if isinstance(text, str) else None)
        if not key:
            key = f"id:{getattr(p, 'id', id(p))}"
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out
