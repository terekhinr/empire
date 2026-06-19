"""Единый интерфейс публикации (ТЗ FINAL §4.1)."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("empire.publish")

CANONICAL_SITE = os.getenv("EMPIRE_CANONICAL_SITE", "https://neverretire.ru").rstrip("/")
RSS_PATH = os.getenv("EMPIRE_DZEN_RSS_PATH", "media/rss.xml")
PENSION_RSS_PATH = os.getenv("EMPIRE_DZEN_RSS_PENSION_PATH", "media/rss_pension.xml")

CHANNELS = ("tg", "vk_wall", "vc_ru", "dzen_rss", "max")


@dataclass
class PublishResult:
    ok: bool
    channel: str
    detail: str = ""
    external_id: str | None = None


def _platform_targets() -> dict[str, dict[str, str | None]]:
    from main import _platform_targets

    return _platform_targets()


async def publish_to_channel(
    session: AsyncSession,
    *,
    content_id: int,
    channel: str,
    source_id: str | None = None,
    text: str | None = None,
    image_path: str | None = None,
    persona_key: str | None = None,
) -> PublishResult:
    """Публикует черновик `content_id` в канал; пишет строку в `publications`."""
    from main import PostDraft, Publication

    ch = (channel or "").strip().lower()
    if ch not in CHANNELS:
        return PublishResult(False, ch, "unknown_channel")

    stmt = select(Publication).where(
        Publication.content_id == content_id,
        Publication.channel == ch,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing and existing.status == "ok":
        return PublishResult(True, ch, "idempotent_skip", existing.external_id)

    draft = await session.get(PostDraft, content_id)
    if not draft:
        return PublishResult(False, ch, "draft_not_found")

    body = text if text is not None else (draft.text_content or "")
    img = image_path if image_path is not None else draft.image_path
    pk = persona_key or draft.persona_key

    if ch == "tg":
        res = await _publish_tg(pk, body, img)
    elif ch == "dzen_rss":
        res = await _publish_dzen_rss(session, draft)
    elif ch == "vk_wall":
        res = _publish_vk_wall(pk, body, img)
    elif ch in ("vc_ru", "max"):
        res = _publish_stub_external(ch)
    else:
        res = PublishResult(False, ch, "unsupported")

    pub = existing or Publication(
        content_id=content_id,
        channel=ch,
        source_id=(source_id or "").strip() or None,
    )
    pub.status = "ok" if res.ok else "error"
    pub.error_message = None if res.ok else res.detail[:500]
    pub.external_id = res.external_id
    pub.updated_at = datetime.now(timezone.utc)
    session.add(pub)
    await session.commit()
    if res.ok:
        try:
            from analytics_db import log_event

            et = "pension_post_published" if pk == "pension" else "post_published"
            log_event(
                et,
                source_id=str(content_id),
                persona_key=pk,
                payload={"channel": ch, "external_id": res.external_id},
            )
        except Exception:
            logger.debug("analytics log_event skip", exc_info=True)
    return res


async def _publish_tg(persona_key: str, text: str, image_path: str | None) -> PublishResult:
    targets = _platform_targets()
    chat_id = (targets.get(persona_key) or {}).get("tg")
    if not chat_id:
        return PublishResult(False, "tg", "no_chat_for_persona")
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        return PublishResult(False, "tg", "no_telegram_token")
    url = f"https://api.telegram.org/bot{token}/"
    try:
        if image_path and os.path.exists(image_path):
            if len(text) <= 1000:
                with open(image_path, "rb") as f:
                    requests.post(
                        url + "sendPhoto",
                        data={"chat_id": chat_id, "caption": text, "parse_mode": "HTML"},
                        files={"photo": f},
                        timeout=60,
                    )
            else:
                with open(image_path, "rb") as f:
                    requests.post(url + "sendPhoto", data={"chat_id": chat_id}, files={"photo": f}, timeout=60)
                requests.post(
                    url + "sendMessage",
                    data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                    timeout=60,
                )
        else:
            requests.post(
                url + "sendMessage",
                data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=60,
            )
        return PublishResult(True, "tg", "sent")
    except Exception as exc:
        logger.warning("tg_publish_error %s", type(exc).__name__)
        return PublishResult(False, "tg", str(exc)[:200])


async def _publish_dzen_rss(session: AsyncSession, draft: Any) -> PublishResult:
    try:
        pk = (getattr(draft, "persona_key", None) or "").strip()
        if pk == "pension":
            from rss_maker import generate_pension_zen_rss

            await generate_pension_zen_rss()
            return PublishResult(True, "dzen_rss", "rss_regenerated", PENSION_RSS_PATH)
        from rss_maker import generate_zen_rss

        await generate_zen_rss()
        return PublishResult(True, "dzen_rss", "rss_regenerated", RSS_PATH)
    except Exception as exc:
        logger.warning("dzen_rss_error %s", type(exc).__name__)
        return PublishResult(False, "dzen_rss", str(exc)[:200])


def _vk_id_from_url(url: str) -> str | None:
    m = re.search(r"(?:vk\.com/)id(\d+)", url or "", re.I)
    return m.group(1) if m else None


def _vk_wall_target(persona_key: str) -> tuple[int | None, bool]:
    """(owner_id, is_group). Группа → отрицательный owner_id, from_group=1."""
    key = (persona_key or "").upper()
    gid = os.getenv(f"VK_GROUP_{key}", "").strip() or os.getenv("VK_GROUP_ID", "").strip()
    personal = os.getenv(f"VK_WALL_PERSONAL_{key}", "").strip().lower() in ("1", "true", "yes")
    if persona_key == "pension":
        if not gid:
            gid = os.getenv("VK_OWNER_PENSION", "").strip()
        if not gid:
            gid = _vk_id_from_url(os.getenv("PENSION_VK_URL", "")) or ""
        if not personal and "id" in (os.getenv("PENSION_VK_URL") or "").lower():
            personal = True
    if not gid:
        return None, False
    if personal:
        return int(gid), False
    return -abs(int(gid)), True


def _strip_html_for_vk(text: str) -> str:
    import re

    t = re.sub(r"<br\s*/?>", "\n", text or "", flags=re.I)
    t = re.sub(r"</p>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return t.replace("&nbsp;", " ").strip()


def _publish_vk_wall(persona_key: str, text: str, image_path: str | None) -> PublishResult:
    token = os.getenv("VK_ACCESS_TOKEN", "").strip()
    if not token:
        return PublishResult(False, "vk_wall", "stub_missing_VK_ACCESS_TOKEN")
    owner_id, is_group = _vk_wall_target(persona_key)
    if owner_id is None:
        return PublishResult(False, "vk_wall", f"stub_missing_VK_GROUP_{(persona_key or '').upper()}")
    message = _strip_html_for_vk(text)[:4096]
    params: dict[str, str | int] = {
        "access_token": token,
        "v": os.getenv("VK_API_VERSION", "5.199"),
        "owner_id": owner_id,
        "from_group": 1 if is_group else 0,
        "message": message,
    }
    # Фото на стену — отдельная итерация; v1 — текст (картинка остаётся в TG).
    try:
        r = requests.post("https://api.vk.com/method/wall.post", data=params, timeout=60)
        data = r.json()
        if "error" in data:
            err = data["error"]
            return PublishResult(False, "vk_wall", f"{err.get('error_code')}: {err.get('error_msg', '')[:120]}")
        post_id = (data.get("response") or {}).get("post_id")
        return PublishResult(True, "vk_wall", "posted", str(post_id) if post_id else None)
    except Exception as exc:
        logger.warning("vk_wall_error %s", type(exc).__name__)
        return PublishResult(False, "vk_wall", str(exc)[:200])


def _publish_stub_external(channel: str) -> PublishResult:
    """Заглушка до появления API-ключей VK / VC / MAX."""
    key = {
        "vk_wall": "VK_ACCESS_TOKEN",
        "vc_ru": "VC_RU_TOKEN",
        "max": "MAX_API_TOKEN",
    }.get(channel, "TOKEN")
    if not os.getenv(key, "").strip():
        return PublishResult(False, channel, f"stub_missing_{key}")
    return PublishResult(False, channel, "adapter_not_implemented")


async def publish_draft_multi(
    session: AsyncSession,
    *,
    content_id: int,
    channels: list[str],
    source_id: str | None = None,
    text: str | None = None,
    image_path: str | None = None,
    persona_key: str | None = None,
) -> list[PublishResult]:
    from empire_flags import load_empire_flags

    if load_empire_flags().get("stop_publications"):
        return [PublishResult(False, c, "stop_publications") for c in channels]
    out: list[PublishResult] = []
    for ch in channels:
        out.append(
            await publish_to_channel(
                session,
                content_id=content_id,
                channel=ch,
                source_id=source_id,
                text=text,
                image_path=image_path,
                persona_key=persona_key,
            )
        )
    return out
