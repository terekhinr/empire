"""Рубрики канала + политика картинок (image_mode)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

IMAGE_MODES = ("generate", "archive_pool", "fixed", "post", "none")

RUBRIC_ALIASES: dict[str, str] = {
    "stepanych": "stepanych",
    "степаныч": "stepanych",
    "garden_curated": "stepanych",
    "curated": "stepanych",
    "lunar": "lunar",
    "луна": "lunar",
    "kizima_lunar": "lunar",
    "kizima": "lunar",
}

GARDEN_DEFAULT_RUBRICS: list[dict[str, Any]] = [
    {
        "id": "stepanych",
        "project_id": "tg:garden",
        "label": "Степаныч",
        "image_mode": "generate",
        "on_missing": "stub",
        "image_provider": "gemini",
        "archive_dir": "media/garden/stepanych",
        "fixed_image_path": None,
        "default_prompt_en": (
            "Central Russia dacha garden, practical gardener aesthetic, "
            "soil and plants, documentary photo, no faces, soft natural light"
        ),
        "enabled": True,
    },
    {
        "id": "lunar",
        "project_id": "tg:garden",
        "label": "Луна",
        "image_mode": "generate",
        "on_missing": "stub",
        "image_provider": "gemini",
        "archive_dir": "media/garden/lunar",
        "fixed_image_path": None,
        "default_prompt_en": (
            "moon calendar gardening theme, night garden Central Russia, "
            "soft moonlight, documentary still life, no faces, no text overlay"
        ),
        "enabled": True,
    },
]

GARDEN_DEFAULT_SLOTS: list[dict[str, Any]] = [
    {"id": "slot-garden-tue-12", "project_id": "tg:garden", "weekday": 1, "time": "12:00", "label": "stepanych", "rubric_id": "stepanych", "enabled": True},
    {"id": "slot-garden-wed-20", "project_id": "tg:garden", "weekday": 2, "time": "20:00", "label": "lunar", "rubric_id": "lunar", "enabled": True},
    {"id": "slot-garden-sat-12", "project_id": "tg:garden", "weekday": 5, "time": "12:00", "label": "stepanych", "rubric_id": "stepanych", "enabled": True},
    {"id": "slot-garden-sat-20", "project_id": "tg:garden", "weekday": 5, "time": "20:00", "label": "lunar", "rubric_id": "lunar", "enabled": True},
]


def normalize_rubric_id(raw: str | None) -> str | None:
    key = (raw or "").strip().lower()
    if not key:
        return None
    return RUBRIC_ALIASES.get(key, key)


def default_rubrics_for_project(project_id: str) -> list[dict[str, Any]]:
    if project_id == "tg:garden":
        return deepcopy(GARDEN_DEFAULT_RUBRICS)
    return []


def ensure_rubrics(data: dict[str, Any]) -> list[dict[str, Any]]:
    rubrics = data.setdefault("rubrics", [])
    if not isinstance(rubrics, list):
        rubrics = []
        data["rubrics"] = rubrics
    have = {(r.get("project_id"), r.get("id")) for r in rubrics if isinstance(r, dict)}
    for r in GARDEN_DEFAULT_RUBRICS:
        key = (r["project_id"], r["id"])
        if key not in have:
            rubrics.append(deepcopy(r))
            have.add(key)
    return rubrics


def ensure_garden_slots(data: dict[str, Any]) -> None:
    """Добавить слоты пилота Сада, если их ещё нет для tg:garden."""
    slots = data.setdefault("slots", [])
    garden_slots = [s for s in slots if s.get("project_id") == "tg:garden"]
    if garden_slots:
        # проставить rubric_id из label если нет
        for s in garden_slots:
            if not s.get("rubric_id"):
                rid = normalize_rubric_id(s.get("label"))
                if rid:
                    s["rubric_id"] = rid
        return
    slots.extend(deepcopy(GARDEN_DEFAULT_SLOTS))


def find_rubric(data: dict[str, Any], *, project_id: str, rubric_id: str | None) -> dict[str, Any] | None:
    rid = normalize_rubric_id(rubric_id)
    for r in ensure_rubrics(data):
        if r.get("project_id") == project_id and r.get("id") == rid:
            return r
    return None


def rubric_public(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": r.get("id"),
        "project_id": r.get("project_id"),
        "label": r.get("label"),
        "image_mode": r.get("image_mode") or "archive_pool",
        "on_missing": r.get("on_missing") or "stub",
        "image_provider": r.get("image_provider") or "gemini",
        "archive_dir": r.get("archive_dir"),
        "fixed_image_path": r.get("fixed_image_path"),
        "default_prompt_en": r.get("default_prompt_en"),
        "enabled": r.get("enabled", True),
    }
