"""Антидубли: нормализация + похожесть за окно дней."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_text(text: str) -> str:
    s = (text or "").lower().replace("ё", "е")
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def similarity(a: str, b: str) -> float:
    """Простая похожесть 0..1 (SequenceMatcher)."""
    from difflib import SequenceMatcher

    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(MSK)
    except ValueError:
        pass
    try:
        return datetime.strptime(str(raw)[:16], "%Y-%m-%d %H:%M").replace(tzinfo=MSK)
    except ValueError:
        return None


def corpus_from_store(
    data: dict[str, Any],
    *,
    project_id: str,
    days: int = 30,
    now: datetime | None = None,
    exclude_ids: set[str] | None = None,
    include_bank: bool = True,
    include_scheduled: bool = True,
) -> list[dict[str, str]]:
    """Тексты постов канала за окно: очередь + база + outbox preview."""
    now = now or datetime.now(MSK)
    cutoff = now - timedelta(days=max(1, days))
    exclude_ids = exclude_ids or set()
    out: list[dict[str, str]] = []

    def add(title: str, body: str, when: str | None, src: str, row_id: str | None = None) -> None:
        if row_id and row_id in exclude_ids:
            return
        dt = _parse_dt(when) or now
        if dt < cutoff:
            return
        text = f"{title or ''}\n{body or ''}".strip()
        if len(normalize_text(text)) < 40:
            return
        out.append({"title": title or "", "body": body or "", "text": text, "src": src})

    for p in data.get("posts") or []:
        if p.get("project_id") != project_id:
            continue
        st = p.get("status") or ""
        if st in ("cancelled",):
            continue
        if not include_scheduled and st in ("scheduled", "queued"):
            continue
        add(
            p.get("title") or "",
            p.get("body") or "",
            p.get("published_at") or p.get("scheduled_at") or p.get("created_at"),
            "posts",
            p.get("id"),
        )

    if include_bank:
        for b in data.get("bank_posts") or []:
            if b.get("project_id") != project_id:
                continue
            if (b.get("status") or "ready") not in ("ready", "active"):
                continue
            add(
                b.get("title") or "",
                b.get("body") or "",
                b.get("created_at") or b.get("last_used_at"),
                "bank",
                b.get("id"),
            )

    for o in data.get("outbox") or []:
        if o.get("project_id") != project_id:
            continue
        add(o.get("title") or "", o.get("body_preview") or "", o.get("at"), "outbox")

    return out


def find_duplicate(
    title: str,
    body: str,
    corpus: list[dict[str, str]],
    *,
    threshold: float = 0.90,
) -> dict[str, Any] | None:
    text = f"{title or ''}\n{body or ''}".strip()
    best: dict[str, Any] | None = None
    best_score = 0.0
    for row in corpus:
        score = similarity(text, row.get("text") or "")
        # заголовок+тело точное после normalize
        if normalize_text(title) and normalize_text(title) == normalize_text(row.get("title") or ""):
            if similarity(body, row.get("body") or "") >= 0.85:
                score = max(score, 0.95)
        if score >= threshold and score > best_score:
            best_score = score
            best = {"score": round(score, 3), "match_title": row.get("title"), "src": row.get("src")}
    return best
