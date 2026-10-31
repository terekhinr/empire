"""Парсер пачки Gemini: --- + YAML frontmatter + тело."""

from __future__ import annotations

import re
from typing import Any

from publisher.rubrics import normalize_rubric_id

POST_BLOCK_RE = re.compile(
    r"---\s*\n(.*?)\n---\s*\n(.*?)(?=\n---\s*\n|\Z)",
    re.DOTALL,
)


def _parse_frontmatter(raw: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in (raw or "").splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip("\"'")
    return meta


def split_gemini_pack(text: str) -> list[dict[str, Any]]:
    """Вернуть список {id, rubric_id, title, body, image_prompt_en, meta}."""
    blob = text or ""
    start = blob.find("---")
    if start < 0:
        return []
    blob = blob[start:]
    out: list[dict[str, Any]] = []
    for fm_raw, body in POST_BLOCK_RE.findall(blob):
        meta = _parse_frontmatter(fm_raw)
        body = (body or "").strip()
        if not body and not meta:
            continue
        title = (
            meta.get("headline")
            or meta.get("title")
            or ""
        ).strip()
        if not title:
            # первая непустая строка тела / markdown heading
            for line in body.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith("#"):
                    title = s.lstrip("#").strip()
                else:
                    # strip simple html/md bold
                    title = re.sub(r"[*_`]+", "", s)[:120]
                break
        rubric_raw = meta.get("rubric") or meta.get("slot") or meta.get("pool") or meta.get("tag") or ""
        out.append(
            {
                "external_id": meta.get("id") or "",
                "rubric_id": normalize_rubric_id(rubric_raw),
                "title": title or "Без названия",
                "body": body,
                "image_prompt_en": meta.get("image_prompt_en") or meta.get("image_prompt") or "",
                "meta": meta,
            }
        )
    return out
