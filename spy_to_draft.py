"""Черновик из spy_signal (ТЗ §4.2 — кнопка «Создать черновик»)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

import spy_config

logger = logging.getLogger("empire.spy_to_draft")

MAX_PER_RUN = int(os.getenv("SPY_DRAFTS_PER_RUN", "0"))


def _topic_from_signal(sig) -> str:
    preview = (sig.post_text or sig.post_ref or "тренд конкурента")[:220]
    comp = (sig.competitor or "конкурент").strip()
    er = sig.er_proxy or "?"
    p_key = (sig.persona_key or "").strip()
    if p_key == "stern":
        task = (
            "ЗАДАЧА: пост Штерна по МОТИВУ (не копия). Другие слова, другой пример, "
            "другая структура. Не упоминай конкурента."
        )
    else:
        task = (
            "ЗАДАЧА: новый пост Михалыча по МОТИВУ (не копия). Другие слова, другой пример, "
            "другая структура. Не упоминай конкурента."
        )
    return f"[Разведка ER={er}] {comp}: {preview}\n\n{task}"


async def create_draft_from_spy(
    session: AsyncSession,
    signal_id: int,
    *,
    skip_image: bool = False,
) -> dict:
    from main import PostDraft, SpySignal, generate_draft_content, generate_image, _record_topic_history

    sig = await session.get(SpySignal, signal_id)
    if not sig:
        return {"ok": False, "error": "signal_not_found"}
    if sig.status == "draft_created" and sig.draft_id:
        return {"ok": True, "draft_id": sig.draft_id, "skipped": "already"}

    p_key = (sig.persona_key or "").strip()
    ok, err = spy_config.can_create_spy_draft(p_key)
    if not ok:
        return {"ok": False, "error": err, "persona_key": p_key}
    topic = _topic_from_signal(sig)
    text, img_p = await generate_draft_content(p_key, topic)
    draft = PostDraft(
        persona_key=p_key,
        text_content=text,
        image_prompt=img_p,
        topic_raw=topic,
        decision="pending",
    )
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    d_id = int(draft.id)

    img_f = None
    if not skip_image:
        try:
            img_f = await generate_image(img_p, d_id, p_key, topic_hint=topic)
        except Exception as exc:
            logger.warning("spy draft image fail %s", type(exc).__name__)
        if img_f:
            d = await session.get(PostDraft, d_id)
            d.image_path = img_f
            await session.commit()

    await _record_topic_history(p_key, topic, d_id)
    sig.status = "draft_created"
    sig.draft_id = d_id
    await session.commit()
    return {"ok": True, "draft_id": d_id, "persona_key": p_key}


async def batch_drafts_from_spy(
    session: AsyncSession,
    *,
    limit: int | None = None,
    skip_image: bool = False,
) -> dict:
    from main import SpySignal

    lim = limit if limit is not None else MAX_PER_RUN
    if lim <= 0 or not spy_config.can_run_spy_pipeline():
        return {"created": 0, "errors": 0, "draft_ids": [], "skipped": "spy_disabled"}
    allowed = list(spy_config.SPY_CONTENT_PERSONAS)
    stmt = (
        select(SpySignal)
        .where(SpySignal.status == "new")
        .where(SpySignal.persona_key.in_(allowed))
        .order_by(desc(SpySignal.anomaly_score))
        .limit(lim)
    )
    signals = (await session.execute(stmt)).scalars().all()
    out = {"created": 0, "errors": 0, "draft_ids": []}
    for sig in signals:
        try:
            res = await create_draft_from_spy(session, int(sig.id), skip_image=skip_image)
            if res.get("ok") and res.get("draft_id"):
                out["created"] += 1
                out["draft_ids"].append(res["draft_id"])
            else:
                out["errors"] += 1
        except Exception as exc:
            logger.exception("spy draft %s", sig.id)
            out["errors"] += 1
            out.setdefault("last_error", str(exc)[:200])
    return out
