"""Банк постов (SocialBee-логика): cooldown и заполнение слотов."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from publisher.schedule import enabled_slots, format_hhmm, next_datetime_for_slot, occupied_keys
from publisher.store import new_id, utc_now_iso

MSK = ZoneInfo("Europe/Moscow")


def _parse_used(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(MSK)
    except ValueError:
        return None


def bank_available(
    bank: list[dict],
    *,
    project_id: str,
    category: str | None = None,
    now: datetime | None = None,
) -> list[dict]:
    now = now or datetime.now(MSK)
    out: list[dict] = []
    for b in bank:
        st = (b.get("status") or "ready").strip() or "ready"
        if st not in ("ready", "active"):
            continue
        if b.get("project_id") != project_id:
            continue
        if category and (b.get("category") or "general") != category:
            continue
        cooldown = int(b.get("cooldown_days") or 21)
        last = _parse_used(b.get("last_used_at"))
        if last is not None and (now - last) < timedelta(days=cooldown):
            continue
        out.append(b)
    # меньше использованных — раньше
    out.sort(key=lambda x: (int(x.get("times_used") or 0), x.get("last_used_at") or ""))
    return out


def pick_bank_post(
    bank: list[dict],
    *,
    project_id: str,
    category: str | None = None,
    now: datetime | None = None,
) -> dict | None:
    avail = bank_available(bank, project_id=project_id, category=category, now=now)
    return avail[0] if avail else None


def mark_bank_used(bank_post: dict, *, when: datetime | None = None) -> None:
    when = when or datetime.now(MSK)
    bank_post["times_used"] = int(bank_post.get("times_used") or 0) + 1
    bank_post["last_used_at"] = when.isoformat()


def bank_days_remaining(data: dict[str, Any], *, posts_per_week: float | None = None) -> int:
    bank = data.get("bank_posts") or []
    ready = [b for b in bank if (b.get("status") or "ready") in ("ready", "active")]
    if not ready:
        return 0
    slots = [s for s in (data.get("slots") or []) if s.get("enabled", True)]
    if posts_per_week is None:
        # грубо: число слотов в неделю
        posts_per_week = float(len(slots) or 3)
    if posts_per_week <= 0:
        posts_per_week = 3.0
    # с учётом cooldown усредняем «уникальные» как len(ready)
    return int(max(0, (len(ready) / posts_per_week) * 7))


def bank_to_queue_post(bank_post: dict, *, scheduled_at: str, slot_id: str | None) -> dict:
    rubric_id = bank_post.get("rubric_id") or bank_post.get("category")
    return {
        "id": new_id("post"),
        "project_id": bank_post.get("project_id"),
        "title": bank_post.get("title") or "Без названия",
        "body": bank_post.get("body") or "",
        "image_path": bank_post.get("image_path"),
        "image_prompt_en": bank_post.get("image_prompt_en"),
        "bank_id": bank_post.get("id"),
        "category": bank_post.get("category") or "general",
        "rubric_id": rubric_id,
        "source_filename": f"bank:{bank_post.get('id')}",
        "slot_id": slot_id,
        "scheduled_at": scheduled_at,
        "status": "scheduled",
        "created_at": utc_now_iso(),
        "published_at": None,
        "last_error": None,
    }


def fill_slots_from_bank(
    data: dict[str, Any],
    *,
    after: datetime | None = None,
    days_ahead: int = 21,
    project_id: str | None = None,
) -> list[dict]:
    """Заполнить пустые окна слотов постами из банка. Возвращает созданные посты."""
    after = after or datetime.now(MSK)
    horizon = after + timedelta(days=max(1, days_ahead))
    bank = data.setdefault("bank_posts", [])
    posts = data.setdefault("posts", [])
    busy = occupied_keys(posts)
    created: list[dict] = []
    slots = enabled_slots(data.get("slots") or [], project_id)

    # Собираем Occurrences слотов в окне
    occurrences: list[tuple[datetime, dict]] = []
    for slot in slots:
        wd = int(slot.get("weekday", -1))
        t = format_hhmm(slot.get("time") or "")
        if not t:
            continue
        cursor = after
        for _ in range(days_ahead + 7):
            dt = next_datetime_for_slot(wd, t, after=cursor, allow_same=True)
            if dt is None or dt > horizon:
                break
            key = (slot.get("project_id"), dt.strftime("%Y-%m-%d %H:%M"))
            if key not in busy:
                occurrences.append((dt, slot))
            cursor = dt + timedelta(minutes=1)

    occurrences.sort(key=lambda x: x[0])
    for dt, slot in occurrences:
        pid = slot.get("project_id")
        from publisher.rubrics import normalize_rubric_id

        rubric_id = normalize_rubric_id(slot.get("rubric_id") or slot.get("label"))
        category = rubric_id or ((slot.get("label") or "").strip() or None)
        # label/rubric как категория; если нет совпадений — без фильтра
        bp = pick_bank_post(bank, project_id=pid, category=category, now=after)
        if bp is None and category:
            bp = pick_bank_post(bank, project_id=pid, category=None, now=after)
        if bp is None:
            continue
        sched = dt.strftime("%Y-%m-%d %H:%M")
        post = bank_to_queue_post(bp, scheduled_at=sched, slot_id=slot.get("id"))
        if rubric_id and not post.get("rubric_id"):
            post["rubric_id"] = rubric_id
        posts.append(post)
        busy.add((pid, sched))
        mark_bank_used(bp, when=after)
        created.append(post)
    return created


def new_bank_post(
    *,
    project_id: str,
    title: str,
    body: str,
    category: str = "general",
    image_path: str | None = None,
    cooldown_days: int = 21,
    rubric_id: str | None = None,
    image_prompt_en: str | None = None,
) -> dict[str, Any]:
    from publisher.rubrics import normalize_rubric_id

    rid = normalize_rubric_id(rubric_id) or normalize_rubric_id(category)
    cat = (category or "").strip() or rid or "general"
    return {
        "id": new_id("bank"),
        "project_id": project_id,
        "category": cat,
        "rubric_id": rid,
        "title": (title or "").strip() or "Без названия",
        "body": (body or "").strip(),
        "image_path": image_path,
        "image_prompt_en": (image_prompt_en or "").strip() or None,
        "cooldown_days": int(cooldown_days or 21),
        "times_used": 0,
        "last_used_at": None,
        "status": "ready",
        "created_at": utc_now_iso(),
    }


def import_gemini_pack_to_bank(
    data: dict[str, Any],
    text: str,
    *,
    project_id: str,
    dedupe: bool = True,
    cooldown_days: int = 21,
) -> dict[str, Any]:
    """Импорт пачки Gemini --- YAML в банк. Антидубли на импорте."""
    from publisher.batch_parse import split_gemini_pack
    from publisher.dedupe import corpus_from_store, find_duplicate

    items = split_gemini_pack(text)
    bank = data.setdefault("bank_posts", [])
    added: list[dict] = []
    skipped_dup: list[dict] = []
    corpus = (
        corpus_from_store(data, project_id=project_id, days=30, include_bank=True)
        if dedupe
        else []
    )
    for item in items:
        title = item.get("title") or "Без названия"
        body = item.get("body") or ""
        if dedupe:
            hit = find_duplicate(title, body, corpus, threshold=0.90)
            if hit:
                skipped_dup.append({"title": title, **hit})
                continue
        post = new_bank_post(
            project_id=project_id,
            title=title,
            body=body,
            category=item.get("rubric_id") or "general",
            rubric_id=item.get("rubric_id"),
            image_prompt_en=item.get("image_prompt_en"),
            cooldown_days=cooldown_days,
        )
        if item.get("external_id"):
            post["external_id"] = item["external_id"]
        bank.append(post)
        added.append(post)
        if dedupe:
            corpus.append(
                {
                    "title": title,
                    "body": body,
                    "text": f"{title}\n{body}".strip(),
                    "src": "bank",
                }
            )
    return {
        "parsed": len(items),
        "added": len(added),
        "skipped_dup": len(skipped_dup),
        "posts": added,
        "dups": skipped_dup,
    }
