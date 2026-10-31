"""Отправка очереди: test/live, рубрики/картинки, антидубли, ops-notify."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from publisher.bank import fill_slots_from_bank
from publisher.catalog import project_by_id
from publisher.dedupe import corpus_from_store, find_duplicate
from publisher.media import resolve_post_image, resolve_rubric_image
from publisher.notify import maybe_send_digest, normalize_bot_settings, notify_tick_results
from publisher.rubrics import find_rubric, normalize_rubric_id
from publisher.store import Store, utc_now_iso

logger = logging.getLogger("empire.publisher")
MSK = ZoneInfo("Europe/Moscow")

LIVE_ENV = "EMPIRE_PUBLISHER_LIVE"


def live_allowed() -> bool:
    return os.getenv(LIVE_ENV, "").strip() in ("1", "true", "yes", "on")


def due_posts(posts: list[dict], *, now: datetime) -> list[dict]:
    now_m = now.astimezone(MSK)
    due = []
    for p in posts:
        if p.get("status") not in ("scheduled", "queued"):
            continue
        sched = p.get("scheduled_at") or ""
        if len(sched) < 16:
            continue
        try:
            dt = datetime.strptime(sched[:16], "%Y-%m-%d %H:%M").replace(tzinfo=MSK)
        except ValueError:
            continue
        if dt <= now_m:
            due.append(p)
    due.sort(key=lambda p: p.get("scheduled_at") or "")
    return due


def tick(
    store: Store,
    *,
    now: datetime | None = None,
    force_ids: list[str] | None = None,
    fill_bank: bool = True,
) -> dict[str, Any]:
    """Обработать наступившие слоты. В test наружу в каналы не шлёт (кроме admin notify)."""
    now = now or datetime.now(MSK)
    results: list[dict] = []
    filled: list[dict] = []
    digest_rec: dict | None = None
    mode = "test"
    with store.mutate() as data:
        mode = (data.get("mode") or "test").strip().lower()
        if mode == "live" and not live_allowed():
            mode = "test"
            data["mode"] = "test"
        settings = normalize_bot_settings(data.get("bot_settings"))
        data["bot_settings"] = settings

        if fill_bank and not force_ids:
            filled = fill_slots_from_bank(data, after=now, days_ahead=21)

        posts = data["posts"]
        if force_ids:
            want = set(force_ids)
            batch = [p for p in posts if p.get("id") in want]
        else:
            batch = due_posts(posts, now=now)

        for post in batch:
            rec = _dispatch_one(post, mode=mode, settings=settings, data=data, now=now)
            results.append(rec)
            data["outbox"].append(rec)
            if rec.get("skipped"):
                post["status"] = "skipped"
                post["last_error"] = rec.get("detail")
                post["published_at"] = utc_now_iso()
            elif rec.get("ok"):
                post["status"] = "test_sent" if mode == "test" else "published"
                post["published_at"] = utc_now_iso()
                post["last_error"] = None
                if rec.get("image_resolved"):
                    post["image_path"] = rec["image_resolved"]
                if rec.get("external_id"):
                    post["external_id"] = rec["external_id"]
            else:
                post["status"] = "failed"
                post["last_error"] = rec.get("detail")
        if len(data["outbox"]) > 400:
            data["outbox"] = data["outbox"][-400:]

        notify_tick_results(settings, results, mode=mode)
        digest_rec = maybe_send_digest(data, now=now)

    return {
        "mode": mode if (results or filled) else (store.load().get("mode") or "test"),
        "sent": results,
        "filled_from_bank": [{"id": p.get("id"), "scheduled_at": p.get("scheduled_at")} for p in filled],
        "digest": digest_rec,
    }


def _dispatch_one(
    post: dict,
    *,
    mode: str,
    settings: dict,
    data: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    pid = post.get("project_id") or ""
    proj = project_by_id(pid)
    rec: dict[str, Any] = {
        "at": utc_now_iso(),
        "mode": mode,
        "post_id": post.get("id"),
        "project_id": pid,
        "kind": (proj or {}).get("kind") or "unknown",
        "title": post.get("title"),
        "scheduled_at": post.get("scheduled_at"),
        "ok": False,
        "skipped": False,
        "detail": "",
        "external_id": None,
        "body_preview": (post.get("body") or "")[:240],
        "image_resolved": None,
        "image_source": None,
        "rubric_id": post.get("rubric_id"),
    }
    if proj is None:
        rec["detail"] = "unknown_project"
        return rec

    body = (post.get("body") or "").strip()
    min_chars = int(settings.get("min_body_chars") or 80)
    if len(body) < min_chars:
        rec["skipped"] = True
        rec["detail"] = f"body_too_short<{min_chars}"
        return rec

    # антидубли перед постом (не банк — иначе false positive с источником)
    days = int(settings.get("dedupe_days") or 30)
    thr = float(settings.get("dedupe_threshold") or 0.90)
    corpus = corpus_from_store(
        data,
        project_id=pid,
        days=days,
        now=now,
        exclude_ids={str(post.get("id") or "")},
        include_bank=False,
        include_scheduled=True,
    )
    dup = find_duplicate(post.get("title") or "", body, corpus, threshold=thr)
    if dup:
        rec["skipped"] = True
        rec["detail"] = f"duplicate@{dup.get('score')}:{dup.get('src')}"
        return rec

    require_image = bool(settings.get("require_image", True)) and proj.get("kind") == "telegram"
    persona = proj.get("persona") or ""
    rubric_id = normalize_rubric_id(post.get("rubric_id") or post.get("category"))
    rubric = find_rubric(data, project_id=pid, rubric_id=rubric_id) if rubric_id else None
    if rubric is None and pid == "tg:garden":
        # слот мог дать rubric через label
        rubric = find_rubric(data, project_id=pid, rubric_id=normalize_rubric_id(post.get("category")))

    if rubric:
        rec["rubric_id"] = rubric.get("id")
        img_path, img_src = resolve_rubric_image(
            post,
            persona=persona,
            rubric=rubric,
            require=require_image and rubric.get("image_mode") != "none",
            allow_generate=True,
        )
        # generate+stub: не skip — stub уже путь
        if img_src == "stub":
            rec["image_resolved"] = img_path
            rec["image_source"] = "stub"
        elif require_image and not img_path and rubric.get("image_mode") != "none":
            rec["skipped"] = True
            rec["detail"] = "no_image_after_resolve"
            rec["image_source"] = img_src
            return rec
        elif rubric.get("image_mode") == "none":
            img_path, img_src = None, "none"
            require_image = False
        else:
            rec["image_resolved"] = img_path
            rec["image_source"] = img_src
    else:
        img_path, img_src = resolve_post_image(post, persona=persona, require=require_image)
        if require_image and not img_path:
            rec["skipped"] = True
            rec["detail"] = "no_image_after_fallback"
            rec["image_source"] = img_src
            return rec
        if not img_path and proj.get("kind") == "site":
            img_path, img_src = resolve_post_image(post, persona=persona, require=False)
        rec["image_resolved"] = img_path
        rec["image_source"] = img_src

    post_for_send = dict(post)
    post_for_send["image_path"] = rec.get("image_resolved") or img_path

    if mode == "test":
        rec["ok"] = True
        detail = "test_outbox"
        if rec.get("image_source") == "stub":
            detail = "test_outbox_stub"
        rec["detail"] = detail
        rec["external_id"] = f"test:{post.get('id')}"
        return rec
    try:
        if proj["kind"] == "telegram":
            rec.update(_publish_telegram(persona, post_for_send))
            if rec.get("ok") and rec.get("image_source") == "stub":
                rec["detail"] = (rec.get("detail") or "") + "|stub"
        elif proj["kind"] == "site":
            rec.update(_publish_site(proj, post_for_send))
        else:
            rec["detail"] = "unsupported_kind"
    except Exception as exc:
        logger.warning("publisher live dispatch failed: %s", type(exc).__name__)
        rec["detail"] = str(exc)[:200]
    return rec


def _publish_telegram(persona: str, post: dict) -> dict[str, Any]:
    import asyncio

    from empire_publish import PublishResult

    text = (post.get("body") or "").strip()
    title = (post.get("title") or "").strip()
    if title and title not in text[:120]:
        text = f"<b>{_esc(title)}</b>\n\n{text}" if "<" not in text else f"{title}\n\n{text}"

    async def _run() -> PublishResult:
        from empire_publish import _publish_tg

        return await _publish_tg(persona, text, post.get("image_path"))

    res = asyncio.run(_run())
    return {
        "ok": bool(res.ok),
        "detail": res.detail,
        "external_id": res.external_id,
    }


def _publish_site(proj: dict, post: dict) -> dict[str, Any]:
    """Сайт: PostDraft status=published (gdepar байки / neverretire articles)."""
    import asyncio

    persona = proj["persona"]
    body = (post.get("body") or "").strip()
    title = (post.get("title") or "").strip()
    if title:
        body = f"<b>{_esc(title)}</b>\n\n{body}"

    async def _run() -> str:
        from main import PostDraft, async_session, init_db

        await init_db()
        async with async_session() as session:
            draft = PostDraft(
                persona_key=persona,
                text_content=body,
                image_path=post.get("image_path"),
                status="published",
                topic_raw=f"[studio] {title}"[:200],
                decision="studio",
            )
            session.add(draft)
            await session.commit()
            await session.refresh(draft)
            return str(draft.id)

    draft_id = asyncio.run(_run())
    return {"ok": True, "detail": "site_published", "external_id": f"draft:{draft_id}"}


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
