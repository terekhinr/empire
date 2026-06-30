"""Канал Штерн: рубрики (якорь JSON + разворот LLM; картинка Commons)."""

from __future__ import annotations

from pathlib import Path

import rubric_posts

_ROOT = Path(__file__).resolve().parent
_RUBRICS_PATH = _ROOT / "data" / "stern_rubrics.json"
_RUBRICS_HISTORY = _ROOT / "data" / "stern_rubrics_used.json"
_RUBRICS_MEDIA = _ROOT / "media" / "stern" / "rubrics"

RUBRIC_ROTATION = (
    "kettlebell_history",
    "athletic_legacy",
    "sports_med",
    "equipment",
    "sports_med",
)

RUBRIC_TOPIC_TAGS = {
    "kettlebell_history": "[История гирь]",
    "athletic_legacy": "[Историческое наследие]",
    "russian_strongmen": "[Русские силачи]",
    "sports_med": "[Спортмед и реабилитация]",
    "equipment": "[Экипировка и лайфхаки]",
    "kettlebell_fitness": "[Гиревой фитнес]",
}


def is_special_slot(slot_value) -> str | None:
    if isinstance(slot_value, dict):
        t = slot_value.get("type") or slot_value.get("special")
        if t:
            return str(t)
    return None


def rubric_key_for_weekday(weekday: int, explicit: str | None = None) -> str:
    if explicit and explicit in RUBRIC_TOPIC_TAGS:
        return explicit
    return RUBRIC_ROTATION[weekday % len(RUBRIC_ROTATION)]


def is_curated_topic(topic_raw: str) -> bool:
    return any(tag in (topic_raw or "") for tag in RUBRIC_TOPIC_TAGS.values()) or (
        "[Историческое наследие]" in (topic_raw or "")
    )


def format_rubric_post(rubric_key: str, entry: dict) -> str:
    data = rubric_posts.load_json(_RUBRICS_PATH)
    meta = (data.get("rubrics") or {}).get(rubric_key, {})
    title = meta.get("title", rubric_key)
    emoji = meta.get("emoji", "🏋️")
    tag = entry.get("tag", "штерн")
    return rubric_posts.format_curated_post(
        title,
        emoji,
        entry,
        hashtags=f"#штерн #{tag} #тренировки #спина #здоровье",
        source_label="Источник",
        commentary_prefix="💬",
    )


def rubric_expansion_rules() -> str:
    return (
        "Канал Штерн: не уходи в соревновательный гиревой спорт (разряды, помост, WKSF, биатлон), "
        "если якорь не про это. Не выдумывай исследования и цифры — только якорь и общие формулировки.\n"
    )


async def build_rubric_slot(
    rubric_key: str | None = None, *, weekday: int = 0
) -> tuple[str, str | None, str | None, dict | None]:
    key = rubric_key_for_weekday(weekday, rubric_key)
    if key == "athletic_legacy":
        import stern_athletic_legacy as sal

        return await sal.build_athletic_legacy_slot(weekday=weekday)
    data = rubric_posts.load_json(_RUBRICS_PATH)
    meta = (data.get("rubrics") or {}).get(key, {})
    entry = rubric_posts.pick_entry(_RUBRICS_PATH, _RUBRICS_HISTORY, rubric=key)
    tag = RUBRIC_TOPIC_TAGS.get(key, "[Штерн · рубрика]")
    if not entry:
        body = f"{tag}\n\nСегодня без выпуска — завтра снова разбор с источником."
        return f"{tag} fallback", body, None, None
    topic = f"{tag} {entry.get('source', '')} (id={entry.get('id', '')})"
    img = await rubric_posts.ensure_entry_image(entry, _RUBRICS_MEDIA, "_default_stern.jpg")
    seed = rubric_posts.make_rubric_seed(
        persona="stern",
        rubric_key=key,
        title=meta.get("title", key),
        emoji=meta.get("emoji", "🏋️"),
        entry=entry,
    )
    return topic, None, img, seed


async def build_rubric_post(rubric_key: str | None = None, *, weekday: int = 0) -> tuple[str, str, str | None]:
    topic, prebuilt, img, _seed = await build_rubric_slot(rubric_key, weekday=weekday)
    if prebuilt:
        return topic, prebuilt, img
    key = rubric_key_for_weekday(weekday, rubric_key)
    entry = rubric_posts.pick_entry(_RUBRICS_PATH, _RUBRICS_HISTORY, rubric=key)
    if not entry:
        return topic, f"{topic}\n\nСегодня без выпуска.", img
    return topic, format_rubric_post(key, entry), img


async def resolve_stern_slot(
    slot_value, *, weekday: int = 0, resolve_topic_fn
) -> tuple[str, str | None, str | None, dict | None]:
    special = is_special_slot(slot_value)
    if special in ("stern_rubric", "curated_rubric", "[SPECIAL:stern_rubric]"):
        explicit = slot_value.get("rubric") if isinstance(slot_value, dict) else None
        return await build_rubric_slot(explicit, weekday=weekday)
    if special in ("weekly_plan", "week_plan", "[SPECIAL:weekly_plan]"):
        return "[План на неделю] Тренировочные цели и задачи.", None, None, {"_kind": "stern_weekly_plan"}
    if special in ("weekly_test", "week_test", "[SPECIAL:weekly_test]"):
        return "[Тест недели] Контроль по плану понедельника.", None, None, {"_kind": "stern_weekly_test"}
    if special in ("weekly_recap", "week_recap", "[SPECIAL:weekly_recap]"):
        import stern_week_arc as swa

        topic, body = swa.build_weekly_recap_post()
        return topic, body, None, None
    if special in ("stern_technique", "technique_video", "[SPECIAL:stern_technique]"):
        import stern_technique as st

        return await st.build_technique_slot()
    if special in ("stern_comic_video", "comic_video", "[SPECIAL:stern_comic_video]"):
        import stern_comic_video as scv

        return await scv.build_comic_slot()
    if special in ("stern_curated", "[SPECIAL:stern_curated]"):
        import stern_curated as sc

        return await sc.build_stern_curated_slot(slot=sc.slot_from_value(slot_value))
    topic = await resolve_topic_fn("stern", slot_value)
    return topic, None, None, None
