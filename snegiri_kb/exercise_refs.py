"""Ссылки YouTube (лендинг) и метаданные мультиков (приложение)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REFS_PATH = Path(__file__).resolve().parent / "exercise_refs_data.json"


@lru_cache(maxsize=1)
def load_refs() -> dict[str, dict]:
    raw = json.loads(REFS_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def ref_by_slug(slug: str) -> dict | None:
    return load_refs().get(slug.replace("-", "_"))


def ref_by_exercise_id(exercise_id: str) -> dict | None:
    for ref in load_refs().values():
        if exercise_id in ref.get("ids", []):
            return ref
    return None


def all_refs_list() -> list[dict]:
    items = []
    for slug, ref in load_refs().items():
        items.append({"slug": slug, **ref})
    track_order = {"S": 0, "K": 1}
    items.sort(key=lambda x: (track_order.get(x.get("track", "K"), 9), x.get("ids", [""])[0]))
    return items
