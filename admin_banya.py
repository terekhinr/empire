"""Веб-модерация банных карточек: /admin/banya.

Простая защищённая токеном (cookie) панель для быстрого триажа драфтов:
смотрим карточку + мини-карту Я.Карт + кнопки «Опубликовать / Скрыть / Pending».
Внизу — модерация ожидающих отзывов.

Авторизация: переменная окружения BANYA_ADMIN_TOKEN; при совпадении ставится
кука banya_admin (httponly, lax). Без токена страница недоступна (503).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Cookie, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from empire_db import BanyaReview, BanyaSpot

BASE_DIR = Path(__file__).parent
_ADMIN_TOKEN = os.getenv("BANYA_ADMIN_TOKEN", "").strip()
COOKIE_NAME = "banya_admin"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 дней

router = APIRouter(prefix="/admin/banya", tags=["admin-banya"])

# templates перетыкаются при подключении (use_templates).
_templates: Jinja2Templates | None = None
_session_factory: sessionmaker | None = None


def configure(templates: Jinja2Templates, session_factory: sessionmaker) -> None:
    """Вызывается из gdepar_app.py при подключении роутера."""
    global _templates, _session_factory
    _templates = templates
    _session_factory = session_factory


def _is_authed(token_cookie: str | None) -> bool:
    if not _ADMIN_TOKEN:
        return False
    return bool(token_cookie) and token_cookie == _ADMIN_TOKEN


def _require_setup() -> None:
    if _templates is None or _session_factory is None:
        raise HTTPException(status_code=500, detail="admin_banya: not configured")
    if not _ADMIN_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="BANYA_ADMIN_TOKEN не задан в .env — модерация выключена.",
        )


# ─── login ──────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, banya_admin: str | None = Cookie(default=None)):
    _require_setup()
    if _is_authed(banya_admin):
        return RedirectResponse(url="/admin/banya", status_code=303)
    assert _templates is not None
    return _templates.TemplateResponse(
        request, "admin_banya_login.html",
        {"request": request, "error": False},
    )


@router.post("/login")
async def login_submit(request: Request, token: str = Form(...)):
    _require_setup()
    if token.strip() == _ADMIN_TOKEN:
        resp = RedirectResponse(url="/admin/banya", status_code=303)
        resp.set_cookie(
            COOKIE_NAME, _ADMIN_TOKEN,
            max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax", path="/admin/banya",
        )
        return resp
    assert _templates is not None
    return _templates.TemplateResponse(
        request, "admin_banya_login.html",
        {"request": request, "error": True},
        status_code=401,
    )


@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/admin/banya/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME, path="/admin/banya")
    return resp


# ─── вспомогательное ────────────────────────────────────────────────────────

def _to_float(v: str | None) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None


def _safe_http_url(raw: str | None) -> str | None:
    """Совпадает с gdepar_app._safe_http_url — только http(s), без циклического импорта."""
    if not raw or not isinstance(raw, str):
        return None
    u = raw.strip()
    if u.startswith("https://") or u.startswith("http://"):
        return u
    return None


def _spot_card(spot: BanyaSpot) -> dict:
    return {
        "id": spot.id,
        "title": spot.title or "",
        "city": spot.city or "",
        "region": spot.region or "",
        "address": spot.address or "",
        "phone": spot.phone or "",
        "heating": spot.heating or "unknown",
        "lat": spot.lat or "",
        "lon": spot.lon or "",
        "yandex_url": _safe_http_url(spot.yandex_url) or "",
        "site_url": _safe_http_url(spot.site_url) or "",
        "twogis_url": _safe_http_url(spot.twogis_url) or "",
        "rating": _to_float(spot.rating_avg),
        "reviews": spot.reviews_total or 0,
        "status": spot.status or "draft",
        "slug": (spot.slug or "").strip(),
    }


async def _fetch_spots(
    session: AsyncSession, *, status: str = "draft", region: str | None,
    min_rating: float, has_phone: bool, has_yandex: bool, limit: int,
) -> list[BanyaSpot]:
    stmt = select(BanyaSpot).where(BanyaSpot.status == status)
    if region:
        stmt = stmt.where(BanyaSpot.region == region.upper())
    if has_phone:
        stmt = stmt.where(BanyaSpot.phone.isnot(None), func.trim(BanyaSpot.phone) != "")
    if has_yandex:
        stmt = stmt.where(BanyaSpot.yandex_url.isnot(None), func.trim(BanyaSpot.yandex_url) != "")
    rows = (await session.execute(stmt)).scalars().all()
    spots = [s for s in rows if (_to_float(s.rating_avg) or 0) >= min_rating]
    spots.sort(
        key=lambda s: (
            -(_to_float(s.rating_avg) or 0),
            -(s.reviews_total or 0),
            s.id,
        )
    )
    return spots[:limit]


# ─── главная панель ─────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def panel(
    request: Request,
    banya_admin: str | None = Cookie(default=None),
    region: str | None = None,
    status: str = "draft",
    min_rating: float = 0.0,
    has_phone: int = 0,
    has_yandex: int = 0,
    limit: int = 60,
):
    _require_setup()
    if not _is_authed(banya_admin):
        return RedirectResponse(url="/admin/banya/login", status_code=303)
    assert _session_factory is not None and _templates is not None

    region_n = (region or "").strip().upper() or None
    status_n = status if status in {"draft", "published", "hidden", "pending"} else "draft"
    limit = max(10, min(200, limit))

    async with _session_factory() as session:
        spots = await _fetch_spots(
            session,
            status=status_n,
            region=region_n,
            min_rating=min_rating,
            has_phone=bool(has_phone),
            has_yandex=bool(has_yandex),
            limit=limit,
        )
        cards = [_spot_card(s) for s in spots]

        counts_rows = (await session.execute(
            select(BanyaSpot.status, BanyaSpot.region, func.count(BanyaSpot.id))
            .group_by(BanyaSpot.status, BanyaSpot.region)
        )).all()

        pending_reviews_rows = (await session.execute(
            select(BanyaReview, BanyaSpot)
            .join(BanyaSpot, BanyaSpot.id == BanyaReview.spot_id)
            .where(BanyaReview.status == "pending")
            .order_by(BanyaReview.id.desc())
            .limit(40)
        )).all()
        pending = [
            {
                "id": rv.id,
                "author": rv.author or "Гость",
                "rating": rv.rating,
                "text": rv.text or "",
                "spot_id": sp.id,
                "spot_title": sp.title or "",
                "spot_city": sp.city or "",
            }
            for rv, sp in pending_reviews_rows
        ]

    counts: dict[str, dict[str, int]] = {}
    for st, rg, n in counts_rows:
        counts.setdefault(st or "?", {})[rg or "?"] = n

    return _templates.TemplateResponse(
        request,
        "admin_banya.html",
        {
            "request": request,
            "spots": cards,
            "counts": counts,
            "pending_reviews": pending,
            "filter_region": region_n or "",
            "filter_status": status_n,
            "filter_min_rating": min_rating,
            "filter_has_phone": bool(has_phone),
            "filter_has_yandex": bool(has_yandex),
            "filter_limit": limit,
        },
    )


# ─── actions API (AJAX) ─────────────────────────────────────────────────────

_ALLOWED_SPOT_STATUSES = {"published", "hidden", "draft", "pending"}


@router.post("/api/spot/{spot_id}/status")
async def api_spot_status(
    spot_id: int,
    payload: dict,
    banya_admin: str | None = Cookie(default=None),
):
    _require_setup()
    if not _is_authed(banya_admin):
        raise HTTPException(status_code=401, detail="unauthorized")
    new_status = (payload or {}).get("status", "").strip()
    if new_status not in _ALLOWED_SPOT_STATUSES:
        raise HTTPException(status_code=400, detail="bad status")
    assert _session_factory is not None
    async with _session_factory() as session:
        spot = await session.get(BanyaSpot, spot_id)
        if not spot:
            raise HTTPException(status_code=404, detail="spot not found")
        spot.status = new_status
        spot.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await session.commit()
    return JSONResponse({"ok": True, "id": spot_id, "status": new_status})


_ALLOWED_REVIEW_STATUSES = {"approved", "hidden", "pending"}


@router.post("/api/review/{rid}/status")
async def api_review_status(
    rid: int,
    payload: dict,
    banya_admin: str | None = Cookie(default=None),
):
    _require_setup()
    if not _is_authed(banya_admin):
        raise HTTPException(status_code=401, detail="unauthorized")
    new_status = (payload or {}).get("status", "").strip()
    if new_status not in _ALLOWED_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="bad status")
    assert _session_factory is not None
    async with _session_factory() as session:
        review = await session.get(BanyaReview, rid)
        if not review:
            raise HTTPException(status_code=404, detail="review not found")
        spot_id = review.spot_id
        review.status = new_status
        await session.commit()
        cnt = (
            await session.execute(
                select(func.count())
                .select_from(BanyaReview)
                .where(
                    BanyaReview.spot_id == spot_id,
                    BanyaReview.status == "approved",
                )
            )
        ).scalar() or 0
        spot = await session.get(BanyaSpot, spot_id)
        if spot:
            spot.reviews_total = cnt
            spot.updated_at = datetime.now(timezone.utc)
            await session.commit()
    return JSONResponse({"ok": True, "id": rid, "status": new_status})
