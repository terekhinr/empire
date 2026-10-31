"""Картинки для автопоста: рубрика image_mode + legacy fallback."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MEDIA_ROOT = ROOT / "media"
ARCHIVE_EXTRA = ROOT / "data" / "publisher" / "archives"

_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def persona_archive_dirs(persona: str) -> list[Path]:
    p = (persona or "").strip()
    dirs = [
        MEDIA_ROOT / p / "classic",
        MEDIA_ROOT / p / "topics",
        MEDIA_ROOT / p / "pool",
        MEDIA_ROOT / p / "books",
        MEDIA_ROOT / p,
        ARCHIVE_EXTRA / p,
    ]
    return [d for d in dirs if d.is_dir()]


def list_archive_images(persona: str, *, extra_dir: str | None = None) -> list[Path]:
    out: list[Path] = []
    dirs = list(persona_archive_dirs(persona))
    if extra_dir:
        raw = Path(extra_dir)
        cand = raw if raw.is_absolute() else (ROOT / raw)
        if cand.is_dir():
            dirs.insert(0, cand)
    for d in dirs:
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in _IMAGE_EXT:
                out.append(f)
    return out


def resolve_existing(path: str | None) -> Path | None:
    raw = (path or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        cand = ROOT / raw
        if cand.is_file():
            return cand
        cand2 = MEDIA_ROOT / raw
        if cand2.is_file():
            return cand2
    if p.is_file():
        return p
    return None


def pick_fallback(persona: str, *, salt: str = "", archive_dir: str | None = None) -> Path | None:
    """Стабильный выбор из архива (не случайный каждый tick)."""
    images = list_archive_images(persona, extra_dir=archive_dir)
    if not images:
        return None
    key = f"{persona}:{archive_dir or ''}:{salt}".encode("utf-8")
    idx = int(hashlib.sha256(key).hexdigest(), 16) % len(images)
    return images[idx]


def resolve_post_image(
    post: dict[str, Any],
    *,
    persona: str,
    require: bool = True,
) -> tuple[str | None, str]:
    """Legacy: явный путь или fallback. reason: ok|fallback|missing."""
    explicit = resolve_existing(post.get("image_path"))
    if explicit is not None:
        return str(explicit), "ok"
    fb = pick_fallback(persona, salt=str(post.get("id") or post.get("title") or ""))
    if fb is not None:
        return str(fb), "fallback"
    if require:
        return None, "missing"
    return None, "missing"


def resolve_rubric_image(
    post: dict[str, Any],
    *,
    persona: str,
    rubric: dict[str, Any] | None,
    require: bool = True,
    allow_generate: bool = True,
) -> tuple[str | None, str]:
    """
    Резолв по image_mode рубрики.
    reason: ok|fixed|pool|generate|stub|none|missing|fallback
    """
    mode = (rubric or {}).get("image_mode") if rubric else None
    if not mode:
        return resolve_post_image(post, persona=persona, require=require)

    mode = str(mode).strip().lower()
    on_missing = str((rubric or {}).get("on_missing") or "stub").strip().lower()
    salt = str(post.get("id") or post.get("title") or "")

    def _stub() -> tuple[str | None, str]:
        from publisher.image_gen import stub_path

        sp = stub_path()
        if sp is not None:
            return str(sp), "stub"
        return None, "missing"

    if mode == "none":
        return None, "none"

    if mode == "fixed":
        fixed = resolve_existing((rubric or {}).get("fixed_image_path"))
        if fixed is not None:
            return str(fixed), "fixed"
        if on_missing == "stub":
            return _stub()
        return None, "missing"

    if mode == "post":
        explicit = resolve_existing(post.get("image_path"))
        if explicit is not None:
            return str(explicit), "ok"
        if on_missing == "stub":
            return _stub()
        return None, "missing" if require else (None, "missing")

    if mode == "archive_pool":
        archive_dir = (rubric or {}).get("archive_dir")
        fb = pick_fallback(persona, salt=salt, archive_dir=archive_dir)
        if fb is not None:
            return str(fb), "pool"
        if on_missing == "stub":
            return _stub()
        return None, "missing"

    if mode == "generate":
        # уже сгенерировано ранее
        explicit = resolve_existing(post.get("image_path"))
        if explicit is not None and "stub.jpg" not in str(explicit):
            return str(explicit), "ok"
        if allow_generate:
            from publisher.image_gen import generate_gemini_image

            prompt = (
                (post.get("image_prompt_en") or "").strip()
                or (rubric or {}).get("default_prompt_en")
                or ""
            )
            if prompt:
                dest_dir = ROOT / "media" / "publisher" / "generated"
                dest = dest_dir / f"{post.get('id') or 'post'}.jpg"
                got = generate_gemini_image(prompt, dest=dest)
                if got is not None:
                    return str(got), "generate"
        if on_missing == "stub":
            return _stub()
        return None, "missing"

    # неизвестный mode → legacy
    return resolve_post_image(post, persona=persona, require=require)
