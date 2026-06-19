"""Сайт «Где Пар» (gdepar.ru) — про парение, дровяные бани и тёплое братство.

Зеркало `гдепар.рф` редиректится на `gdepar.ru` через Nginx (301).
Контент берётся из empire.db (persona_key='gdepar', status='published').
Карта бань — таблица banya_spots (status='published', координаты обязательны).
"""

from __future__ import annotations

import html as html_std
import asyncio
import hashlib
import json
import logging
import os
import secrets
import time
import re
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from collections.abc import AsyncIterator
from typing import Literal, Self
from urllib.parse import urlencode

from pydantic import BaseModel, Field, model_validator
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
import uvicorn

from main import BanyaSpot, BanyaReview, DATABASE_URL, PostDraft, normalize_clip_list
import admin_banya

BASE_DIR = Path(__file__).parent
CANONICAL_HOST = os.getenv("GDEPAR_CANONICAL_HOST", "gdepar.ru").strip() or "gdepar.ru"
CANONICAL_BASE_URL = f"https://{CANONICAL_HOST}".rstrip("/")
_GDEPAR_DEFAULT_OG_IMAGE_PATH = "/static/gdepar/logos/03-drop.svg"
# Сброс кэша CSS у клиентов после правок вёрстки (можно переопределить в .env).
GDEPAR_ASSET_VERSION = os.getenv("GDEPAR_ASSET_VERSION", "20260520c").strip() or "20260520c"
_HTML_NO_CACHE = {"Cache-Control": "no-cache, must-revalidate"}
_SEO_STATIC_CACHE = {"Cache-Control": "public, max-age=3600"}
_HTML_404_HEADERS = {**_HTML_NO_CACHE, "X-Robots-Tag": "noindex"}
_GDEPAR_HSTS_MAX_AGE = os.getenv("GDEPAR_HSTS_MAX_AGE", "").strip()


def _request_is_https(request: Request) -> bool:
    """Учитывает прокси: последний X-Forwarded-Proto в цепочке."""
    if request.url.scheme == "https":
        return True
    chain = (request.headers.get("x-forwarded-proto") or "").lower()
    if not chain:
        return False
    return chain.split(",")[-1].strip() == "https"


def _html_public_page_headers(canonical_url: str) -> dict[str, str]:
    """Как _HTML_NO_CACHE плюс HTTP Link rel=canonical (главная, /map с учётом query)."""
    hdr = dict(_HTML_NO_CACHE)
    hdr["Link"] = f'<{canonical_url}>; rel="canonical"'
    return hdr


def _gdepar_share_image_url() -> str:
    """Абсолютный URL картинки по умолчанию для OG/Twitter главной и /map."""
    return f"{CANONICAL_BASE_URL}{_GDEPAR_DEFAULT_OG_IMAGE_PATH}"


_raw_metrika = os.getenv("YANDEX_METRIKA_ID", "").strip()
YANDEX_METRIKA_ID = _raw_metrika if _raw_metrika.isdigit() else ""

_assistant_logger = logging.getLogger("gdepar.assistant")
_ASSISTANT_RL_BUCKETS: dict[str, list[float]] = {}
_assistant_rl_lock = asyncio.Lock()
_assistant_cache_lock = asyncio.Lock()
_assistant_cache: dict[str, tuple[float, dict]] = {}
_GDEPAR_TRANSPARENCY_NOTE = "Ответ сформирован автоматически; проверьте контакты на карточке бани."

# Подпись «МО» в фильтре: города Подмосковья (не «Москва»). Расширяйте по мере наполнения базы.
MO_OBLAST_CITIES = frozenset(
    {
        "Балашиха",
        "Химки",
        "Подольск",
        "Мытищи",
        "Королёв",
        "Люберцы",
        "Красногорск",
        "Одинцово",
        "Долгопрудный",
        "Реутов",
        "Щёлково",
        "Жуковский",
        "Пушкино",
        "Раменское",
        "Ногинск",
        "Домодедово",
        "Сергиев Посад",
        "Электросталь",
        "Коломна",
        "Орехово-Зуево",
        "Видное",
        "Истра",
        "Лобня",
        "Дмитров",
        "Солнечногорск",
        "Клин",
        "Чехов",
        "Ступино",
        "Серпухов",
        "Звенигород",
        "Краснознаменск",
        "Дубна",
        "Протвино",
        "Фрязино",
        "Лыткарино",
        "Котельники",
        "Павловский Посад",
        "Электроугли",
        "Дзержинский",
    }
)

_CITY_LABELS = {"Санкт-Петербург": "Питер"}
_CITY_ORDER_FIRST = ("Москва", "МО", "Санкт-Петербург")


def map_canonical_url(city_n: str | None, heating: str, visited_only: bool) -> str:
    """Канонический URL страницы карты с теми же query-параметрами, что и в UI."""
    qs: list[tuple[str, str]] = []
    if city_n:
        qs.append(("city", city_n))
    if heating and heating != "all":
        qs.append(("heating", heating))
    if visited_only:
        qs.append(("visited", "1"))
    path = f"{CANONICAL_BASE_URL}/map"
    if not qs:
        return path
    return path + "?" + urlencode(qs)


def gdepar_schema_org_markup(base_url: str) -> Markup:
    """JSON-LD для главной: WebSite + Organization (без пользовательского ввода)."""
    site_url = f"{base_url}/"
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": "Где Пар",
                "url": site_url,
                "description": (
                    "Где Пар — путеводитель по дровяным баням и каменкам. "
                    "Где жарко, где парят, где встречают как своего."
                ),
            },
            {"@type": "Organization", "name": "Где Пар", "url": site_url},
        ],
    }
    return Markup(json.dumps(payload, ensure_ascii=False))


def gdepar_map_schema_org_markup(base_url: str, page_url: str) -> Markup:
    """JSON-LD для /map: WebPage и связь с сайтом."""
    site_root = f"{base_url}/"
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": page_url,
                "name": "Карта бань — Где Пар",
                "url": page_url,
                "description": (
                    "Карта общественных и дровяных бань — Где Пар. "
                    "Фильтры по городу, типу нагрева, личным визитам."
                ),
                "isPartOf": {"@type": "WebSite", "name": "Где Пар", "url": site_root},
            }
        ],
    }
    return Markup(json.dumps(payload, ensure_ascii=False))


def _page_modified_iso(dt: datetime | None) -> str | None:
    """Дата изменения в RFC 3339 UTC (Z) для JSON-LD и meta."""
    if not dt:
        return None
    try:
        d = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _http_last_modified_header(dt: datetime | None) -> str | None:
    """Значение заголовка Last-Modified (HTTP-date, GMT)."""
    if not dt:
        return None
    try:
        d = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        return format_datetime(d.astimezone(timezone.utc), usegmt=True)
    except Exception:
        return None


def _spot_page_http_headers(
    updated_at: datetime | None,
    *,
    canonical_page_url: str | None = None,
) -> dict[str, str]:
    """Cache-Control, Last-Modified и опционально Link rel=canonical (RFC 8288)."""
    hdr = dict(_HTML_NO_CACHE)
    lm = _http_last_modified_header(updated_at)
    if lm:
        hdr["Last-Modified"] = lm
    if canonical_page_url:
        hdr["Link"] = f'<{canonical_page_url}>; rel="canonical"'
    return hdr


def _not_modified_since_client_header(header_val: str | None, updated_at: datetime | None) -> bool:
    """True, если по If-Modified-Since можно ответить 304 (не новее даты клиента)."""
    if not header_val or not isinstance(header_val, str) or not updated_at:
        return False
    try:
        client_dt = parsedate_to_datetime(header_val.strip())
    except (TypeError, ValueError):
        return False
    try:
        srv = updated_at if updated_at.tzinfo else updated_at.replace(tzinfo=timezone.utc)
        srv = srv.astimezone(timezone.utc).replace(microsecond=0)
        client_dt = client_dt.astimezone(timezone.utc).replace(microsecond=0)
    except Exception:
        return False
    return srv <= client_dt


def _safe_http_url(raw: str | None) -> str | None:
    """Только http(s): — без javascript: и прочих схем в пользовательских URL."""
    if not raw or not isinstance(raw, str):
        return None
    u = raw.strip()
    if u.startswith("https://") or u.startswith("http://"):
        return u
    return None


def _cover_url_for_output(raw: str | None) -> str | None:
    """Обложка для API/страницы: абсолютный http(s) или путь от корня сайта."""
    if not raw or not isinstance(raw, str):
        return None
    c = raw.strip()
    if not c:
        return None
    if c.startswith(("https://", "http://")):
        return c
    if c.startswith("/"):
        return c
    return None


def _spot_og_image_url(cover: str | None, canonical_base: str) -> str:
    """Абсолютный URL для og:image / JSON-LD image: обложка, относительный путь от корня сайта или капля."""
    root = canonical_base.rstrip("/")
    fallback = f"{root}/static/gdepar/logos/03-drop.svg"
    if not cover or not isinstance(cover, str):
        return fallback
    c = cover.strip()
    if c.startswith(("https://", "http://")):
        return c
    if c.startswith("/"):
        return root + c
    return fallback


def _schema_review_snippet(text: str, max_len: int = 480) -> str:
    """Короткий текст отзыва для JSON-LD без лишних переводов строк."""
    t = (text or "").strip()
    if not t:
        return ""
    t = " ".join(t.split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip(",.; ") + "…"


def gdepar_spot_schema_org_markup(
    site_root: str,
    page_url: str,
    spot_d: dict,
    reviews: list[dict] | None = None,
    page_updated_at: datetime | None = None,
    page_created_at: datetime | None = None,
    primary_image_url: str | None = None,
) -> Markup:
    """JSON-LD: LocalBusiness + BreadcrumbList + WebPage + Review (до 10 отзывов на странице)."""
    name = (spot_d.get("title") or "Баня").strip() or "Баня"
    root = site_root.rstrip("/")
    place_id = f"{page_url}#place"
    lb: dict = {
        "@type": "LocalBusiness",
        "@id": place_id,
        "name": name,
        "url": page_url,
    }
    if primary_image_url:
        lb["image"] = primary_image_url
    addr = (spot_d.get("address") or "").strip()
    city = (spot_d.get("city") or "").strip()
    if addr or city:
        ao: dict = {"@type": "PostalAddress"}
        if addr:
            ao["streetAddress"] = addr
        if city:
            ao["addressLocality"] = city
        lb["address"] = ao
    lat = spot_d.get("lat")
    lon = spot_d.get("lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        lb["geo"] = {"@type": "GeoCoordinates", "latitude": lat, "longitude": lon}
    try:
        rtc = int(spot_d.get("reviews_total") or 0)
        ra = spot_d.get("rating_avg")
        if rtc > 0 and ra is not None:
            av = float(ra)
            if av > 0:
                lb["aggregateRating"] = {
                    "@type": "AggregateRating",
                    "ratingValue": round(av, 2),
                    "reviewCount": rtc,
                }
    except (TypeError, ValueError):
        pass

    same_as: list[str] = []
    for key in ("yandex_url", "twogis_url", "site_url"):
        u = spot_d.get(key)
        if isinstance(u, str) and (s := u.strip()):
            same_as.append(s)
    if same_as:
        lb["sameAs"] = same_as

    tel_raw = spot_d.get("phone")
    if isinstance(tel_raw, str):
        t_tel = tel_raw.strip()
        if t_tel:
            lb["telephone"] = t_tel[:80]

    crumbs = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Где Пар",
                "item": f"{root}/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Карта бань",
                "item": f"{root}/map",
            },
            {"@type": "ListItem", "position": 3, "name": name, "item": page_url},
        ],
    }

    graph: list[dict] = [lb, crumbs]
    wp: dict = {
        "@type": "WebPage",
        "@id": f"{page_url}#webpage",
        "url": page_url,
        "name": name,
        "isPartOf": {"@type": "WebSite", "name": "Где Пар", "url": f"{root}/"},
        "mainEntity": {"@id": place_id},
    }
    mod_iso = _page_modified_iso(page_updated_at)
    if mod_iso:
        wp["dateModified"] = mod_iso
    pub_iso = _page_modified_iso(page_created_at)
    if pub_iso:
        wp["datePublished"] = pub_iso
    drop_img = f"{root}/static/gdepar/logos/03-drop.svg"
    if primary_image_url and primary_image_url != drop_img:
        wp["primaryImageOfPage"] = {"@type": "ImageObject", "url": primary_image_url}
    graph.append(wp)
    if reviews:
        for r in reviews[:10]:
            rid = r.get("id")
            if rid is None:
                continue
            body = _schema_review_snippet(r.get("text") or "")
            rating_val: float | None = None
            if r.get("rating") is not None:
                try:
                    rvf = float(r["rating"])
                    if rvf > 0:
                        rating_val = rvf
                except (TypeError, ValueError):
                    pass
            if not body and rating_val is None:
                continue
            who = str(r.get("author") or "Гость").strip()[:100] or "Гость"
            rv: dict = {
                "@type": "Review",
                "@id": f"{page_url}#review-{rid}",
                "author": {"@type": "Person", "name": who},
                "itemReviewed": {"@id": place_id},
            }
            if body:
                rv["reviewBody"] = body
            if rating_val is not None:
                rv["reviewRating"] = {"@type": "Rating", "ratingValue": rating_val, "bestRating": 5}
            graph.append(rv)

    payload = {
        "@context": "https://schema.org",
        "@graph": graph,
    }
    return Markup(json.dumps(payload, ensure_ascii=False))


def _normalize_city_param(city: str | None) -> str | None:
    if not city:
        return None
    s = city.strip()
    if s == "Питер":
        return "Санкт-Петербург"
    return s or None


def _city_options_for_ui(db_cities: list[str]) -> list[tuple[str, str]]:
    merged = set(db_cities) | {"МО", "Санкт-Петербург"}
    head = [c for c in _CITY_ORDER_FIRST if c in merged]
    tail = sorted(merged.difference(head))
    return [(c, _CITY_LABELS.get(c, c)) for c in head + tail]


def _review_datetime(rv: BanyaReview) -> datetime | None:
    return rv.published_at or rv.fetched_at


def _serialize_review(rv: BanyaReview) -> dict:
    return {
        "id": rv.id,
        "author": rv.author or "Гость",
        "rating": rv.rating,
        "text": rv.text or "",
        "source": rv.source,
    }


_REVIEW_SNIPPET_BOILERPLATE_RE = re.compile(
    r"(?:Отзыв слишком длинный[^\n.]*\.?\s*)+"
    r"|(?:Оригинал полностью:\s*Яндекс\.Карты\.?\s*)+",
    re.IGNORECASE,
)


def _clean_review_snippet_text(raw: str) -> str:
    t = (raw or "").strip()
    if not t:
        return ""
    t = _REVIEW_SNIPPET_BOILERPLATE_RE.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def _review_snippet_words(raw: str, max_words: int = 28) -> str:
    cleaned = _clean_review_snippet_text(raw)
    if not cleaned:
        return ""
    words = cleaned.split()
    snip = " ".join(words[:max_words])
    if len(words) > max_words:
        snip += "…"
    return snip


def _reviews_rank_for_highlights(reviews_sample: list[BanyaReview]) -> list[BanyaReview]:
    def score_key(r: BanyaReview) -> float:
        dt = _review_datetime(r)
        ts = dt.timestamp() if dt else 0.0
        rt = (r.rating or 0) / 5.0
        return ts + rt * 86400.0 * 45.0

    return sorted(reviews_sample, key=score_key, reverse=True)


def _reviews_summary_stats(reviews_sample: list[BanyaReview]) -> dict:
    dts = [_review_datetime(r) for r in reviews_sample]
    dts_ok = [d for d in dts if d is not None]
    last_dt = max(dts_ok) if dts_ok else None
    rated_vals = [r.rating for r in reviews_sample if r.rating is not None and r.rating > 0]
    avg = round(sum(rated_vals) / len(rated_vals), 1) if rated_vals else None
    return {
        "count": len(reviews_sample),
        "last_date": last_dt.strftime("%d.%m.%Y") if last_dt else None,
        "avg_rating": avg,
    }


def _reviews_summary_highlights(reviews_sample: list[BanyaReview], *, max_items: int = 4) -> list[dict]:
    out: list[dict] = []
    for r in _reviews_rank_for_highlights(reviews_sample):
        snip = _review_snippet_words(r.text or "", 26)
        if len(snip) < 12:
            continue
        who = (r.author or "Гость").strip()[:64] or "Гость"
        item: dict = {"quote": snip, "author": who}
        if r.rating is not None and r.rating > 0:
            item["rating"] = round(float(r.rating), 1)
        out.append(item)
        if len(out) >= max_items:
            break
    return out


def _reviews_summary_parts_heuristic(reviews_sample: list[BanyaReview]) -> dict:
    stats = _reviews_summary_stats(reviews_sample)
    highlights = _reviews_summary_highlights(reviews_sample)
    intro = f"Сводка по {stats['count']} свежим одобренным отзывам на «Где Пар»."
    return {"intro": intro, "stats": stats, "highlights": highlights, "bullets": []}


def _reviews_summary_plain(parts: dict) -> str:
    lines: list[str] = []
    intro = (parts.get("intro") or "").strip()
    if intro:
        lines.append(intro)
    stats = parts.get("stats") or {}
    if stats.get("last_date"):
        lines.append(f"Последний отзыв: {stats['last_date']}.")
    if stats.get("avg_rating") is not None:
        lines.append(f"Средняя оценка: {stats['avg_rating']} из 5.")
    for b in parts.get("bullets") or []:
        t = str(b).strip()
        if t:
            lines.append(f"• {t}")
    if not (parts.get("bullets") or []):
        for h in parts.get("highlights") or []:
            q = (h.get("quote") or "").strip()
            who = (h.get("author") or "Гость").strip()
            if q:
                lines.append(f"• «{q}» — {who}")
    return "\n".join(lines).strip()


def _reviews_summary_html(parts: dict) -> str:
    intro = (parts.get("intro") or "").strip()
    stats = parts.get("stats") or {}
    bullets = [str(b).strip() for b in (parts.get("bullets") or []) if str(b).strip()][:5]
    highlights = parts.get("highlights") or []

    chunks: list[str] = ['<div class="gdepar-summary-card">']
    if intro:
        chunks.append(f'<p class="gdepar-summary-intro">{html_std.escape(intro)}</p>')

    meta_bits: list[str] = []
    if stats.get("count"):
        meta_bits.append(f"{int(stats['count'])} отзывов в выборке")
    if stats.get("last_date"):
        meta_bits.append(f"последний — {html_std.escape(str(stats['last_date']))}")
    if stats.get("avg_rating") is not None:
        meta_bits.append(f"средняя оценка {stats['avg_rating']} из 5")
    if meta_bits:
        chunks.append('<ul class="gdepar-summary-meta">')
        for bit in meta_bits:
            chunks.append(f"<li>{bit}</li>")
        chunks.append("</ul>")

    if bullets:
        chunks.append('<p class="gdepar-summary-lead">Что отмечают гости:</p>')
        chunks.append('<ul class="gdepar-summary-bullets">')
        for b in bullets:
            chunks.append(f"<li>{html_std.escape(b)}</li>")
        chunks.append("</ul>")
    elif highlights:
        chunks.append('<p class="gdepar-summary-lead">Фрагменты из отзывов:</p>')
        chunks.append('<ul class="gdepar-summary-quotes">')
        for h in highlights:
            q = (h.get("quote") or "").strip()
            if not q:
                continue
            who = html_std.escape((h.get("author") or "Гость").strip())
            rating = h.get("rating")
            cite = who
            if rating is not None:
                cite += f' · {rating} из 5'
            chunks.append(
                f'<li><blockquote>«{html_std.escape(q)}»</blockquote><cite>{cite}</cite></li>'
            )
        chunks.append("</ul>")

    chunks.append("</div>")
    return "".join(chunks)


def _apply_summary_parts_to_payload(payload: dict, parts: dict) -> None:
    payload["summary"] = _reviews_summary_plain(parts)
    payload["summary_html"] = _reviews_summary_html(parts)
    payload["summary_stats"] = parts.get("stats")
    payload["summary_highlights"] = parts.get("highlights") or []
    payload["summary_bullets"] = parts.get("bullets") or []


def _popup_summary_parts_from_llm(parsed: dict, reviews_sample: list[BanyaReview]) -> dict | None:
    intro = (parsed.get("intro") or parsed.get("summary") or "").strip()
    bullets_raw = parsed.get("bullets")
    bullets: list[str] = []
    if isinstance(bullets_raw, list):
        bullets = [str(b).strip() for b in bullets_raw if str(b).strip()]
    elif isinstance(bullets_raw, str) and bullets_raw.strip():
        bullets = [bullets_raw.strip()]
    bullets = [b[:220] for b in bullets][:5]
    if len(intro) < 16 and not bullets:
        return None
    if len(intro) > 520:
        intro = intro[:517] + "…"
    return {
        "intro": intro,
        "stats": _reviews_summary_stats(reviews_sample),
        "highlights": [],
        "bullets": bullets,
    }


def _reviews_list_payload(reviews: list[BanyaReview], list_limit: int) -> dict:
    """Только список отзывов и дата последнего — без сводки (кнопка «Показать отзывы»)."""
    if not reviews:
        return {"summary": None, "last_review_at": None, "reviews": []}
    dts = [_review_datetime(r) for r in reviews]
    dts_ok = [d for d in dts if d is not None]
    last_dt = max(dts_ok) if dts_ok else None
    by_date = sorted(
        reviews,
        key=lambda r: _review_datetime(r) or datetime.min,
        reverse=True,
    )
    listed = by_date[:list_limit]
    return {
        "summary": None,
        "last_review_at": last_dt.isoformat() if last_dt else None,
        "reviews": [_serialize_review(r) for r in listed],
    }


def _build_reviews_block_payload(reviews_sample: list[BanyaReview], list_limit: int) -> dict:
    """Сводка без LLM: статистика + короткие цитаты списком (не одним абзацем)."""
    if not reviews_sample:
        return {
            "summary": (
                "Одобренных отзывов пока нет — после сбора и модерации здесь появится сводка и дата "
                "последнего отзыва."
            ),
            "summary_html": None,
            "summary_stats": None,
            "summary_highlights": [],
            "summary_bullets": [],
            "last_review_at": None,
            "reviews": [],
            "transparency_note": _GDEPAR_TRANSPARENCY_NOTE,
        }

    dts = [_review_datetime(r) for r in reviews_sample]
    dts_ok = [d for d in dts if d is not None]
    last_dt = max(dts_ok) if dts_ok else None

    by_date = sorted(
        reviews_sample,
        key=lambda r: _review_datetime(r) or datetime.min,
        reverse=True,
    )
    listed = by_date[:list_limit]

    parts = _reviews_summary_parts_heuristic(reviews_sample)
    payload: dict = {
        "last_review_at": last_dt.isoformat() if last_dt else None,
        "reviews": [_serialize_review(r) for r in listed],
        "transparency_note": _GDEPAR_TRANSPARENCY_NOTE,
    }
    _apply_summary_parts_to_payload(payload, parts)
    return payload


async def _approved_reviews_for_spot_page(spot_id: int, limit: int = 12) -> list[dict]:
    """Одобренные отзывы для HTML карточки бани (тот же порядок, что у reviews-block без сводки)."""
    list_limit = max(1, min(20, limit))
    order_col = func.coalesce(BanyaReview.published_at, BanyaReview.fetched_at)
    async with async_session() as session:
        stmt = (
            select(BanyaReview)
            .where(
                BanyaReview.spot_id == spot_id,
                BanyaReview.status == "approved",
            )
            .order_by(desc(order_col), desc(BanyaReview.id))
            .limit(list_limit)
        )
        result = await session.execute(stmt)
        reviews = list(result.scalars().all())
    return [_serialize_review(r) for r in reviews]


_GDEPAR_ASST_SESSION_COOKIE = "gdepar_asst_sid"


def _assistant_client_fp(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        ip = (xff.split(",")[0] or "").strip()
    else:
        ip = (request.client.host if request.client else "") or ""
    ua = request.headers.get("user-agent") or ""
    raw = f"{ip}|{ua}".encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()[:16]


def _assistant_session_key(request: Request) -> str:
    """Анонимный id вкладки из cookie (ТЗ §3 MVP); без cookie — «-»."""
    sid = (request.cookies.get(_GDEPAR_ASST_SESSION_COOKIE) or "").strip()
    if 8 <= len(sid) <= 64 and re.fullmatch(r"[a-zA-Z0-9_-]+", sid):
        return sid[:32]
    return "-"


def _log_assistant_timing(
    request: Request,
    *,
    route: str,
    elapsed_ms: float,
    page: Literal["home", "map", "spot"] | None,
    payload: dict | None,
) -> None:
    raw = os.getenv("GDEPAR_ASSISTANT_LOG", "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return
    p = payload or {}
    _assistant_logger.info(
        "timing route=%s ms=%.0f client_fp=%s session_id=%s page=%s llm=%s cached=%s stub=%s rate_limited=%s",
        route,
        elapsed_ms,
        _assistant_client_fp(request),
        _assistant_session_key(request),
        page if page else "-",
        bool(p.get("llm")),
        bool(p.get("cached")),
        bool(p.get("stub")),
        bool(p.get("rate_limited")),
    )


def _assistant_len_bucket(n: int) -> str:
    if n < 1:
        return "0"
    if n < 80:
        return "1-79"
    if n < 400:
        return "80-399"
    return "400+"


def _assistant_message_likely_spam(message_stripped: str) -> bool:
    """Грубая эвристика без внешних API (ТЗ §3 защита): спам/мусор до LLM и кэша."""
    s = message_stripped.strip()
    if len(s) < 10:
        return False
    nospace = re.sub(r"\s+", "", s)
    if len(nospace) >= 12 and len(set(nospace)) <= 2:
        return True
    low = s.lower()
    if low.count("http://") + low.count("https://") > 5:
        return True
    return False


_assistant_toxic_re_cache: tuple[str, re.Pattern[str] | None] | None = None


def _assistant_toxic_pattern() -> re.Pattern[str] | None:
    """Опционально: `GDEPAR_ASSISTANT_TOXIC_REGEX` (пусто — не фильтровать)."""
    global _assistant_toxic_re_cache
    raw = os.getenv("GDEPAR_ASSISTANT_TOXIC_REGEX", "").strip()
    if not raw:
        _assistant_toxic_re_cache = None
        return None
    if _assistant_toxic_re_cache is not None and _assistant_toxic_re_cache[0] == raw:
        return _assistant_toxic_re_cache[1]
    try:
        pat = re.compile(raw, re.IGNORECASE | re.UNICODE)
    except re.error:
        _assistant_logger.warning("assistant_toxic_regex_invalid")
        _assistant_toxic_re_cache = (raw, None)
        return None
    _assistant_toxic_re_cache = (raw, pat)
    return pat


def _assistant_message_toxic_blocked(message_stripped: str) -> bool:
    pat = _assistant_toxic_pattern()
    if pat is None:
        return False
    return pat.search(message_stripped) is not None


def _log_assistant_stub_request(
    request: Request, message_stripped: str, page: Literal["home", "map", "spot"] | None = None
) -> None:
    """Без текста запроса: длина, корзина как на фронте, SHA256-префикс IP|UA (см. ТЗ MVP)."""
    raw = os.getenv("GDEPAR_ASSISTANT_LOG", "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return
    n = len(message_stripped)
    bucket = _assistant_len_bucket(n)
    fp = _assistant_client_fp(request)
    pg = page if page else "-"
    sk = _assistant_session_key(request)
    _assistant_logger.info(
        "stub query len=%s len_bucket=%s client_fp=%s session_id=%s page=%s",
        n,
        bucket,
        fp,
        sk,
        pg,
    )


def _assistant_rl_per_minute() -> int:
    v = os.getenv("GDEPAR_ASSISTANT_RL_PER_MIN", "24").strip()
    if not v:
        return 24
    try:
        return max(0, int(v))
    except ValueError:
        return 24


def _assistant_rl_disabled() -> bool:
    return os.getenv("GDEPAR_ASSISTANT_RL_DISABLE", "").strip().lower() in ("1", "true", "yes", "on")


async def _assistant_rate_allows(request: Request) -> bool:
    """Скользящее окно 60 с по client_fp; при лимите 0 — без ограничений."""
    if _assistant_rl_disabled():
        return True
    limit = _assistant_rl_per_minute()
    if limit <= 0:
        return True
    fp = _assistant_client_fp(request)
    now = time.monotonic()
    window = 60.0
    async with _assistant_rl_lock:
        seq = _ASSISTANT_RL_BUCKETS.setdefault(fp, [])
        cutoff = now - window
        while seq and seq[0] < cutoff:
            seq.pop(0)
        if len(seq) >= limit:
            return False
        seq.append(now)
        return True


class GdeparAssistantSessionMiddleware(BaseHTTPMiddleware):
    """Анонимная cookie-сессия для корреляции логов помощника (ТЗ §3 MVP)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/") or request.url.path.startswith("/static/"):
            return response
        sid = (request.cookies.get(_GDEPAR_ASST_SESSION_COOKIE) or "").strip()
        if sid and 8 <= len(sid) <= 64 and re.fullmatch(r"[a-zA-Z0-9_-]+", sid):
            return response
        new_sid = secrets.token_hex(16)
        secure = _request_is_https(request)
        response.set_cookie(
            _GDEPAR_ASST_SESSION_COOKIE,
            new_sid,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            samesite="lax",
            secure=secure,
            path="/",
        )
        return response


class GdeparSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Базовые заголовки для HTML и API одного процесса."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        if request.url.path.startswith("/admin"):
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        if (
            _GDEPAR_HSTS_MAX_AGE.isdigit()
            and int(_GDEPAR_HSTS_MAX_AGE) > 0
            and _request_is_https(request)
        ):
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={int(_GDEPAR_HSTS_MAX_AGE)}",
            )
        return response


app = FastAPI(title="Где Пар", docs_url=None, redoc_url=None)
app.add_middleware(GdeparAssistantSessionMiddleware)
if os.getenv("GDEPAR_SECURITY_HEADERS", "1").strip().lower() not in ("0", "false", "no", "off"):
    app.add_middleware(GdeparSecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
# В image_path постов лежат пути вида "media/draft_NNN.jpg" — отдаём как статику.
MEDIA_DIR = BASE_DIR / "media"
if MEDIA_DIR.exists():
    app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# Жёсткий whitelist инлайн-разметки: эскейпим всё, затем включаем обратно только
# те теги, что LLM использует осмысленно — жирный/курсив/перенос/мягкий разрыв.
# Это безопаснее, чем |safe (никаких скриптов/onclick/iframe-инжектов).
_ALLOWED_INLINE_TAGS = ("b", "strong", "i", "em", "u", "s", "br", "blockquote")
_TAG_RE = re.compile(
    r"&lt;(/?)("
    + "|".join(_ALLOWED_INLINE_TAGS)
    + r")\s*/?&gt;",
    flags=re.IGNORECASE,
)
_HASHTAG_RE = re.compile(r"(?<![\w&])#([A-Za-zА-Яа-яЁё0-9_]{2,40})")


def _enable_safe_tags(escaped: str) -> str:
    def repl(m: re.Match) -> str:
        close = m.group(1)
        tag = m.group(2).lower()
        return f"<{close}{tag}>"

    return _TAG_RE.sub(repl, escaped)


def post_media_url(raw: str | None) -> str | None:
    """URL обложки байки: media/… → /media/…, абсолютный путь проекта → относительный."""
    if not raw or not isinstance(raw, str):
        return None
    c = raw.strip().replace("\\", "/")
    if not c:
        return None
    if c.startswith(("https://", "http://")):
        return c
    root = str(BASE_DIR).replace("\\", "/")
    if c.startswith(root + "/"):
        c = c[len(root) + 1 :]
    c = c.lstrip("/")
    if c.startswith("media/"):
        return "/" + c
    if c.startswith("static/"):
        return "/" + c
    return "/" + c


def safe_post_html(raw: str | None) -> Markup:
    """Готовит текст поста к рендеру в HTML:
    - эскейпит всё (XSS-защита),
    - возвращает разрешённые инлайн-теги,
    - подсвечивает хэштеги,
    - превращает одиночные переносы строк в <br>.
    """
    if not raw:
        return Markup("")
    text = html_std.escape(str(raw))
    text = _enable_safe_tags(text)
    text = _HASHTAG_RE.sub(r'<span class="tag">#\1</span>', text)
    text = text.replace("\r\n", "\n").replace("\n", "<br>\n")
    return Markup(text)


templates.env.filters["safe_post_html"] = safe_post_html
templates.env.filters["post_media_url"] = post_media_url
templates.env.filters["gdepar_http_url"] = lambda u: _safe_http_url(u) or ""


_ENGRAVINGS_DIR = BASE_DIR / "static" / "gdepar" / "bayki"


def _engraving_pool() -> list[str]:
    """Сканирует папку гравюр один раз за процесс, возвращает список URL-путей."""
    if not _ENGRAVINGS_DIR.exists():
        return []
    return sorted(
        f"/static/gdepar/bayki/{p.name}"
        for p in _ENGRAVINGS_DIR.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )


_ENGRAVINGS_CACHE: list[str] | None = None


def engraving_for(post_id: int | None) -> str | None:
    """Детерминированно выбирает гравюру для поста без своей картинки (по id)."""
    global _ENGRAVINGS_CACHE
    if _ENGRAVINGS_CACHE is None:
        _ENGRAVINGS_CACHE = _engraving_pool()
    pool = _ENGRAVINGS_CACHE
    if not pool or post_id is None:
        return None
    return pool[int(post_id) % len(pool)]


templates.env.globals["engraving_for"] = engraving_for


@app.exception_handler(StarletteHTTPException)
async def gdepar_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """404 для HTML — своя страница; /api/* оставляем стандартный JSON."""
    if exc.status_code != 404 or request.url.path.startswith("/api/"):
        return await http_exception_handler(request, exc)
    return templates.TemplateResponse(
        request,
        "gdepar_404.html",
        {
            "request": request,
            "canonical_host": CANONICAL_HOST,
            "canonical_base_url": CANONICAL_BASE_URL,
            "asset_version": GDEPAR_ASSET_VERSION,
            "metrika_id": YANDEX_METRIKA_ID,
            "metrika_page": "home",
        },
        status_code=404,
        headers=_HTML_404_HEADERS,
    )


engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

admin_banya.configure(templates, async_session)
app.include_router(admin_banya.router)


def _spot_to_dict(spot: BanyaSpot) -> dict:
    tags: list = []
    if spot.tags_json:
        try:
            tags = json.loads(spot.tags_json)
        except Exception:
            tags = []
    clips = normalize_clip_list(spot.clips_json)
    lat_f: float | None = None
    lon_f: float | None = None
    try:
        if spot.lat is not None and str(spot.lat).strip() != "":
            lat_f = float(spot.lat)
        if spot.lon is not None and str(spot.lon).strip() != "":
            lon_f = float(spot.lon)
    except (TypeError, ValueError):
        lat_f = lon_f = None
    return {
        "id": spot.id,
        "slug": spot.slug,
        "title": spot.title,
        "city": spot.city,
        "address": spot.address,
        "lat": lat_f,
        "lon": lon_f,
        "heating": spot.heating or "unknown",
        "kind": spot.kind or "public",
        "visited": bool(spot.visited),
        "site_url": _safe_http_url(spot.site_url),
        "phone": spot.phone,
        "yandex_url": _safe_http_url(spot.yandex_url),
        "twogis_url": _safe_http_url(spot.twogis_url),
        "description": (spot.description or "")[:500],
        "tags": tags,
        "clips": clips,
        "rating_avg": spot.rating_avg,
        "reviews_total": spot.reviews_total or 0,
        "cover_url": _cover_url_for_output(spot.cover_url),
    }


_CITY_TO_REGION = {"МО": "MO", "Санкт-Петербург": "SPB", "Москва": "MSK"}


def _apply_banya_filters(stmt, city: str | None, heating: str, visited_only: bool):
    stmt = stmt.where(BanyaSpot.status == "published")
    if city:
        region = _CITY_TO_REGION.get(city)
        if region:
            stmt = stmt.where(BanyaSpot.region == region)
        else:
            stmt = stmt.where(BanyaSpot.city == city)
    if heating and heating != "all":
        stmt = stmt.where(BanyaSpot.heating == heating)
    if visited_only:
        stmt = stmt.where(BanyaSpot.visited == 1)
    return stmt


def _assistant_cache_ttl_seconds() -> int:
    raw = os.getenv("GDEPAR_ASSISTANT_CACHE_SECONDS", "0").strip()
    if not raw or raw.lower() in ("0", "off", "false", "no"):
        return 0
    try:
        return max(60, min(86400, int(raw)))
    except ValueError:
        return 0


def _assistant_cache_key(
    message_stripped: str,
    page: Literal["home", "map", "spot"] | None,
    city_raw: str | None,
    heat_raw: str | None,
    *,
    llm_mode: bool,
    seen_spot_ids: list[int] | None = None,
) -> str:
    norm_msg = " ".join(message_stripped.split()).lower()[:2000]
    c = (city_raw or "").strip().lower()[:120]
    h = (heat_raw or "").strip().lower()[:24]
    p = (page or "") or ""
    seen_ns: list[int] = []
    for x in seen_spot_ids or []:
        try:
            i = int(x)
            if i > 0:
                seen_ns.append(i)
        except (TypeError, ValueError):
            continue
    seen = sorted(set(seen_ns))[:48]
    blob = json.dumps(
        {"m": norm_msg, "p": p, "c": c, "h": h, "llm": int(bool(llm_mode)), "s": seen},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _assistant_llm_enabled() -> bool:
    if not os.getenv("OPENROUTER_API_KEY", "").strip():
        return False
    return os.getenv("GDEPAR_ASSISTANT_LLM", "").strip().lower() in ("1", "true", "yes", "on")


def _assistant_llm_percent() -> int:
    """Доля клиентов (client_fp за сутки UTC), для которых разрешён вызов LLM помощника; 0–100."""
    try:
        return max(0, min(100, int(os.getenv("GDEPAR_ASSISTANT_LLM_PCT", "100"))))
    except ValueError:
        return 100


def _assistant_llm_rollout_for_client_today(client_fp: str) -> bool:
    if not _assistant_llm_enabled():
        return False
    pct = _assistant_llm_percent()
    if pct <= 0:
        return False
    if pct >= 100:
        return True
    day = datetime.now(timezone.utc).date().isoformat()
    h = int(hashlib.sha256(f"gdepar_asst_llm|{client_fp}|{day}".encode("utf-8")).hexdigest(), 16)
    return (h % 100) < pct


def _assistant_llm_model() -> str:
    return (os.getenv("GDEPAR_ASSISTANT_MODEL") or "openai/gpt-4o-mini").strip()


def _assistant_llm_timeout_sec() -> float:
    try:
        return max(5.0, min(90.0, float(os.getenv("GDEPAR_ASSISTANT_LLM_TIMEOUT", "25"))))
    except ValueError:
        return 25.0


def _assistant_llm_max_tokens() -> int:
    try:
        return max(120, min(2000, int(os.getenv("GDEPAR_ASSISTANT_LLM_MAX_TOKENS", "650"))))
    except ValueError:
        return 650


def _assistant_llm_user_prompt_max_chars() -> int:
    """Макс. длина текста роли user (символы Unicode); каталог/отзывы ужимаются (ТЗ §3)."""
    try:
        return max(8000, min(100_000, int(os.getenv("GDEPAR_ASSISTANT_PROMPT_MAX_CHARS", "48000"))))
    except ValueError:
        return 48000


def _assistant_catalog_for_llm_line(spot: BanyaSpot) -> str:
    tags = ""
    if spot.tags_json:
        try:
            t = json.loads(spot.tags_json)
            if isinstance(t, list) and t:
                tags = ",".join(str(x) for x in t[:8] if x)
        except Exception:
            tags = ""
    desc = (spot.description or "").replace("\n", " ").strip()
    if len(desc) > 160:
        desc = desc[:157] + "…"
    return f"{spot.id}|{spot.city or ''}|{spot.heating or ''}|{spot.title}|{tags}|{desc}"


def _assistant_reviews_per_spot_cap() -> int:
    """Сколько одобренных отзывов на точку подмешать в промпт LLM (0 = не грузить)."""
    try:
        return max(0, min(8, int(os.getenv("GDEPAR_ASSISTANT_REVIEW_SNIPPETS_PER_SPOT", "2"))))
    except ValueError:
        return 2


def _assistant_reviews_fetch_cap() -> int:
    """Верхняя граница строк отзывов из БД до усечения по per-spot."""
    try:
        return max(20, min(500, int(os.getenv("GDEPAR_ASSISTANT_REVIEW_FETCH_CAP", "150"))))
    except ValueError:
        return 150


def _assistant_review_line_for_llm(rv: BanyaReview) -> str:
    sid = int(rv.spot_id) if rv.spot_id is not None else 0
    rt = rv.rating if rv.rating is not None else ""
    txt = (rv.text or "").replace("\n", " ").strip()
    if len(txt) > 220:
        txt = txt[:217] + "…"
    return f"review|{sid}|{rt}|{txt}"


async def _assistant_load_catalog_for_prompt(
    city_n: str | None, heating: str, limit: int
) -> tuple[list[str], set[int], dict[int, str], str]:
    """Каталог точек + блок текста одобренных отзывов для RAG (ТЗ §3 v1)."""
    per_spot = _assistant_reviews_per_spot_cap()
    fetch_cap = _assistant_reviews_fetch_cap()
    async with async_session() as session:
        stmt = select(BanyaSpot).order_by(BanyaSpot.city, BanyaSpot.title)
        stmt = _apply_banya_filters(stmt, city_n, heating or "all", visited_only=False)
        stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
        spot_id_list = [int(s.id) for s in rows if s.id is not None]
        review_lines: list[str] = []
        if per_spot > 0 and spot_id_list:
            order_col = func.coalesce(BanyaReview.published_at, BanyaReview.fetched_at)
            stmt_r = (
                select(BanyaReview)
                .where(
                    BanyaReview.status == "approved",
                    BanyaReview.spot_id.in_(spot_id_list),
                )
                .order_by(BanyaReview.spot_id, desc(order_col), desc(BanyaReview.id))
                .limit(fetch_cap)
            )
            result_r = await session.execute(stmt_r)
            all_rv = list(result_r.scalars().all())
            counts: dict[int, int] = {}
            for rv in all_rv:
                if rv.spot_id is None:
                    continue
                sid = int(rv.spot_id)
                if sid not in spot_id_list:
                    continue
                if counts.get(sid, 0) >= per_spot:
                    continue
                counts[sid] = counts.get(sid, 0) + 1
                review_lines.append(_assistant_review_line_for_llm(rv))
    lines = [_assistant_catalog_for_llm_line(s) for s in rows]
    ids = {int(s.id) for s in rows if s.id is not None}
    id_slug: dict[int, str] = {}
    for s in rows:
        if s.id is None:
            continue
        sl = (getattr(s, "slug", None) or "").strip()
        if sl:
            id_slug[int(s.id)] = sl
    reviews_txt = "\n".join(review_lines)
    return lines, ids, id_slug, reviews_txt


def _assistant_stub_payload(filter_hint: str) -> dict:
    return {
        "reply": (
            "Сейчас подбор идёт по каталогу и фильтрам карты без языковой модели. "
            "Уточните город и тип нагрева на карте; в карточке бани есть «Дай саммари» по отзывам."
            f"{filter_hint}"
        ),
        "stub": True,
        "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
    }


async def _assistant_stub_recommendations(
    city_raw: str | None,
    heat_raw: str | None,
    seen_spot_ids: list[int] | None,
    *,
    max_picks: int = 7,
    min_picks: int = 0,
    fetch_cap: int = 28,
) -> list[dict]:
    """Точки из каталога для заглушки (ТЗ §2.2): без LLM, те же фильтры, что у карты."""
    city_n = _normalize_city_param(city_raw) if city_raw and str(city_raw).strip() else None
    heat_v = (heat_raw or "").strip().lower() if heat_raw else "all"
    if heat_v not in ("all", "wood", "electric", "mixed", "unknown"):
        heat_v = "all"
    seen_set: set[int] = set()
    for x in seen_spot_ids or []:
        try:
            i = int(x)
            if i > 0:
                seen_set.add(i)
        except (TypeError, ValueError):
            continue
    cap = max(max_picks, min(40, fetch_cap), min_picks if min_picks > 0 else 0)
    async with async_session() as session:
        stmt = select(BanyaSpot).order_by(BanyaSpot.city, BanyaSpot.title)
        stmt = _apply_banya_filters(stmt, city_n, heat_v, visited_only=False)
        stmt = stmt.limit(cap)
        result = await session.execute(stmt)
        rows = list(result.scalars().all())
    unseen = [s for s in rows if s.id is not None and int(s.id) not in seen_set]
    seen_rows = [s for s in rows if s.id is not None and int(s.id) in seen_set]
    ordered = unseen + seen_rows
    if min_picks > 0 and len(ordered) >= min_picks:
        n_take = min(max_picks, max(min_picks, len(ordered)))
    else:
        n_take = min(max_picks, len(ordered))
    reason = "точка из каталога по фильтрам карты (без ИИ; откройте на карте или в карточке)"
    picks: list[dict] = []
    for s in ordered[:n_take]:
        if s.id is None:
            continue
        sid = int(s.id)
        sl = (getattr(s, "slug", None) or "").strip()
        title = ((s.title or "").strip()[:240] or f"Баня {sid}")
        picks.append({"spot_id": sid, "slug": sl, "title": title, "reason": reason})
    return picks


async def _assistant_cache_get(key: str) -> dict | None:
    ttl = _assistant_cache_ttl_seconds()
    if ttl <= 0:
        return None
    now = time.monotonic()
    async with _assistant_cache_lock:
        dead = [k for k, (exp, _) in _assistant_cache.items() if exp < now]
        for k in dead:
            del _assistant_cache[k]
        ent = _assistant_cache.get(key)
        if not ent:
            return None
        exp, payload = ent
        if exp < now:
            del _assistant_cache[key]
            return None
        return dict(payload)


async def _assistant_cache_set(key: str, payload: dict) -> None:
    ttl = _assistant_cache_ttl_seconds()
    if ttl <= 0:
        return
    store = {k: v for k, v in payload.items() if k != "cached"}
    async with _assistant_cache_lock:
        _assistant_cache[key] = (time.monotonic() + ttl, store)


def _log_assistant_cache_hit(request: Request, page: Literal["home", "map", "spot"] | None) -> None:
    raw = os.getenv("GDEPAR_ASSISTANT_LOG", "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return
    fp = _assistant_client_fp(request)
    pg = page if page else "-"
    _assistant_logger.info("stub cache_hit client_fp=%s page=%s", fp, pg)


async def _assistant_llm_reply_payload(
    message_stripped: str,
    city_raw: str | None,
    heat_raw: str | None,
    seen_spot_ids: list[int] | None,
) -> dict | None:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None
    composed = await _assistant_llm_compose_user_message(
        message_stripped, city_raw, heat_raw, seen_spot_ids, streaming=False
    )
    if not composed:
        return None
    user, allowed_ids, id_slug = composed
    model = _assistant_llm_model()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": f"{CANONICAL_BASE_URL}/",
                    "X-Title": "Gdepar assistant",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Ты консультант каталога бань gdepar.ru. Отвечаешь только по переданным "
                                "строкам каталога и блоку одобренных отзывов (префикс review|); "
                                "не выдумываешь бани, адреса, ссылки и отзывы. "
                                "В picks при желании можно добавить целое score 0–100 (релевантность)."
                            ),
                        },
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.25,
                    "max_tokens": _assistant_llm_max_tokens(),
                },
                timeout=_assistant_llm_timeout_sec(),
            )
    except Exception as exc:
        _assistant_logger.warning("assistant_llm_http_error %s", type(exc).__name__)
        return None
    if resp.status_code != 200:
        _assistant_logger.warning("assistant_llm_status=%s", resp.status_code)
        return None
    try:
        data = resp.json()
        content = (data["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return None
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*", "", content)
        content = re.sub(r"\s*```\s*$", "", content).strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        _assistant_logger.warning("assistant_llm_json_decode")
        return None
    reply = (parsed.get("reply") or "").strip()
    picks_raw = parsed.get("picks") if isinstance(parsed.get("picks"), list) else parsed.get("recommendations")
    picks_out = _assistant_picks_from_llm_items(
        picks_raw if isinstance(picks_raw, list) else [], allowed_ids, id_slug
    )
    seen_pick_ids = {int(r["spot_id"]) for r in picks_out}
    if len(picks_out) < 1:
        _assistant_logger.info("assistant_llm_no_valid_picks")
        return None
    if len(picks_out) < 3 <= len(allowed_ids):
        pad_reason = "дополнение из каталога по фильтрам карты (без ИИ)."
        filler = await _assistant_stub_recommendations(
            city_raw, heat_raw, seen_spot_ids, max_picks=14, fetch_cap=56
        )
        for row in filler:
            try:
                sid = int(row.get("spot_id"))
            except (TypeError, ValueError):
                continue
            if sid in seen_pick_ids or sid not in allowed_ids:
                continue
            seen_pick_ids.add(sid)
            picks_out.append(
                {
                    "spot_id": sid,
                    "slug": str(row.get("slug") or "").strip(),
                    "title": str(row.get("title") or "").strip()[:240] or f"Баня {sid}",
                    "reason": pad_reason,
                }
            )
            if len(picks_out) >= 7:
                break
        if len(picks_out) < 3:
            _assistant_logger.info("assistant_llm_underfilled_picks picks=%s allowed=%s", len(picks_out), len(allowed_ids))
            return None
    if len(reply) < 12:
        reply = "Ниже — точки из каталога по вашему запросу; откройте карту и карточки бань для контактов."
    if len(reply) > 2800:
        reply = reply[:2797] + "…"
    return {
        "reply": reply,
        "stub": False,
        "llm": True,
        "model": model,
        "recommendations": picks_out,
        "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
    }


_ASSISTANT_STREAM_PICKS_MARKER = "---PICKS---"
_ASSISTANT_STREAM_PARTIAL_MARKERS = (
    "---PICKS--",
    "---PICKS-",
    "---PICKS",
    "---PICK",
    "---PIC",
    "---PI",
    "---P",
    "---",
)


def _assistant_sse_bytes(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def _assistant_stream_reply_delta(accumulated: str, sent_len: int) -> tuple[str, int]:
    """Текст ответа до маркера ---PICKS--- для потоковой отдачи в UI."""
    cutoff = accumulated.find(_ASSISTANT_STREAM_PICKS_MARKER)
    if cutoff >= 0:
        visible = accumulated[:cutoff].rstrip()
    else:
        visible = accumulated
        for tail in _ASSISTANT_STREAM_PARTIAL_MARKERS:
            if visible.endswith(tail):
                visible = visible[: -len(tail)]
                break
    if len(visible) <= sent_len:
        return "", sent_len
    chunk = visible[sent_len:]
    return chunk, sent_len + len(chunk)


def _assistant_picks_from_llm_items(
    picks_raw: list,
    allowed_ids: set[int],
    id_slug: dict[int, str],
) -> list[dict]:
    picks_out: list[dict] = []
    seen_pick_ids: set[int] = set()
    if not isinstance(picks_raw, list):
        return picks_out
    for item in picks_raw[:14]:
        if not isinstance(item, dict):
            continue
        try:
            sid = int(item.get("spot_id"))
        except (TypeError, ValueError):
            continue
        if sid not in allowed_ids or sid in seen_pick_ids:
            continue
        seen_pick_ids.add(sid)
        title = str(item.get("title") or "").strip()[:240]
        reason = str(item.get("reason") or "").strip()[:400]
        slug = id_slug.get(sid, "")
        row: dict = {"spot_id": sid, "slug": slug, "title": title, "reason": reason}
        sc = item.get("score")
        if sc is not None:
            try:
                iv = int(round(float(sc)))
                if 0 <= iv <= 100:
                    row["score"] = iv
            except (TypeError, ValueError):
                pass
        picks_out.append(row)
        if len(picks_out) >= 7:
            break
    return picks_out


async def _assistant_llm_compose_user_message(
    message_stripped: str,
    city_raw: str | None,
    heat_raw: str | None,
    seen_spot_ids: list[int] | None,
    *,
    streaming: bool,
) -> tuple[str, set[int], dict[int, str]] | None:
    city_n = _normalize_city_param(city_raw) if city_raw and str(city_raw).strip() else None
    heat_v = (heat_raw or "").strip().lower() if heat_raw else "all"
    if heat_v not in ("all", "wood", "electric", "mixed", "unknown"):
        heat_v = "all"
    try:
        catalog_limit = max(10, min(80, int(os.getenv("GDEPAR_ASSISTANT_CATALOG_LIMIT", "40"))))
    except ValueError:
        catalog_limit = 40
    lines, allowed_ids, id_slug, reviews_txt = await _assistant_load_catalog_for_prompt(
        city_n, heat_v, catalog_limit
    )
    seen_ns: list[int] = []
    for x in seen_spot_ids or []:
        try:
            i = int(x)
            if i > 0:
                seen_ns.append(i)
        except (TypeError, ValueError):
            continue
    seen = sorted(set(seen_ns))[:48]
    seen_block = ""
    if seen:
        seen_block = (
            "\n\nНа этом устройстве пользователь недавно смотрел spot_id: "
            + ", ".join(str(x) for x in seen)
            + ". По возможности предлагай другие точки из каталога с близким качеством, "
            "если они подходят под запрос (не повторяй без необходимости)."
        )
    if streaming:
        tail_inst = (
            "\n\nФормат ответа строго:\n"
            "1) Сначала 2–4 предложения по-русски обычным текстом (без markdown, без JSON).\n"
            f"2) С новой строки ровно маркер {_ASSISTANT_STREAM_PICKS_MARKER}\n"
            "3) Следующей строкой JSON-массив UTF-8 без markdown: "
            '[{"spot_id":число,"title":"как в каталоге","reason":"кратко","score":0-100 опционально}] '
            "от 3 до 7 элементов, только spot_id из каталога."
        )
    else:
        tail_inst = (
            '\n\nВерни один JSON-объект UTF-8 без markdown: {"reply":"2-4 предложения по-русски",'
            '"picks":[{"spot_id":число,"title":"как в каталоге","reason":"кратко","score":число0-100опционально"}]} '
            "picks: от 3 до 7 элементов, только spot_id из каталога; без текста вне JSON."
        )
    cap = _assistant_llm_user_prompt_max_chars()
    work_lines: list[str] = list(lines)
    work_reviews = reviews_txt
    user = ""
    for _ in range(96):
        if work_lines:
            catalog_txt = "\n".join(work_lines)
        else:
            catalog_txt = "(каталог пуст для выбранных фильтров — расширьте город или нагрев на карте.)"
        if work_reviews.strip():
            reviews_block = (
                "\n\nОдобренные отзывы (только этот блок; строки вида review|spot_id|rating|текст; "
                "не придумывай отзывы и не приписывай их другим spot_id):\n"
                f"{work_reviews}"
            )
        else:
            reviews_block = (
                "\n\n(Одобренных отзывов в этой выборке нет — опирайся только на строки каталога.)"
            )
        user = (
            f"Запрос пользователя:\n{message_stripped}\n\n"
            f"Фильтры UI: город={city_raw or '—'}, нагрев={heat_raw or '—'}.\n\n"
            "Каталог (только эти spot_id допустимы в picks):\n"
            f"{catalog_txt}{reviews_block}{seen_block}{tail_inst}"
        )
        if len(user) <= cap:
            break
        if len(work_lines) > 1:
            work_lines = work_lines[: max(1, (len(work_lines) * 3) // 4)]
            continue
        if work_reviews.strip() and len(work_reviews) > 600:
            nr = max(300, (len(work_reviews) * 2) // 3)
            cut = work_reviews[:nr]
            if "\n" in cut:
                cut = cut.rsplit("\n", 1)[0]
            work_reviews = cut + "\n…[отзывы усечены по лимиту размера запроса]"
            continue
        if work_lines:
            work_lines = []
            continue
        user = user[: max(2000, cap - 1)] + "…"
        break
    if len(user) > cap:
        user = user[: max(2000, cap - 1)] + "…"
    return user, allowed_ids, id_slug


async def _openrouter_chat_stream_deltas(
    *,
    api_key: str,
    model: str,
    user: str,
    title: str,
) -> AsyncIterator[str]:
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": f"{CANONICAL_BASE_URL}/",
                    "X-Title": title,
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Ты консультант каталога бань gdepar.ru. Отвечаешь только по переданным "
                                "строкам каталога и блоку одобренных отзывов (префикс review|); "
                                "не выдумываешь бани, адреса, ссылки и отзывы. "
                                "В picks при желании можно добавить целое score 0–100 (релевантность)."
                            ),
                        },
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.25,
                    "max_tokens": _assistant_llm_max_tokens(),
                    "stream": True,
                },
                timeout=_assistant_llm_timeout_sec(),
            ) as resp:
                if resp.status_code != 200:
                    _assistant_logger.warning("assistant_llm_stream_status=%s", resp.status_code)
                    return
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        obj = json.loads(payload)
                        choice = (obj.get("choices") or [{}])[0]
                        delta = choice.get("delta") or {}
                        part = delta.get("content") or ""
                        if part:
                            yield part
                    except (json.JSONDecodeError, IndexError, KeyError, TypeError):
                        continue
    except Exception as exc:
        _assistant_logger.warning("assistant_llm_stream_http_error %s", type(exc).__name__)


async def _assistant_llm_payload_from_stream_body(
    accumulated: str,
    allowed_ids: set[int],
    id_slug: dict[int, str],
    city_raw: str | None,
    heat_raw: str | None,
    seen_spot_ids: list[int] | None,
    model: str,
) -> dict | None:
    parts = accumulated.split(_ASSISTANT_STREAM_PICKS_MARKER, 1)
    reply = parts[0].strip()
    picks_raw: list = []
    if len(parts) > 1:
        picks_blob = parts[1].strip()
        if picks_blob.startswith("```"):
            picks_blob = re.sub(r"^```[a-zA-Z]*\s*", "", picks_blob)
            picks_blob = re.sub(r"\s*```\s*$", "", picks_blob).strip()
        try:
            parsed = json.loads(picks_blob)
            if isinstance(parsed, list):
                picks_raw = parsed
            elif isinstance(parsed, dict):
                picks_raw = parsed.get("picks") if isinstance(parsed.get("picks"), list) else []
        except json.JSONDecodeError:
            _assistant_logger.warning("assistant_llm_stream_picks_decode")
    picks_out = _assistant_picks_from_llm_items(picks_raw, allowed_ids, id_slug)
    if len(picks_out) < 1:
        _assistant_logger.info("assistant_llm_stream_no_valid_picks")
        return None
    if len(picks_out) < 3 <= len(allowed_ids):
        pad_reason = "дополнение из каталога по фильтрам карты (без ИИ)."
        filler = await _assistant_stub_recommendations(
            city_raw, heat_raw, seen_spot_ids, max_picks=14, fetch_cap=56
        )
        seen_pick_ids = {int(r["spot_id"]) for r in picks_out}
        for row in filler:
            try:
                sid = int(row.get("spot_id"))
            except (TypeError, ValueError):
                continue
            if sid in seen_pick_ids or sid not in allowed_ids:
                continue
            seen_pick_ids.add(sid)
            picks_out.append(
                {
                    "spot_id": sid,
                    "slug": str(row.get("slug") or "").strip(),
                    "title": str(row.get("title") or "").strip()[:240] or f"Баня {sid}",
                    "reason": pad_reason,
                }
            )
            if len(picks_out) >= 7:
                break
        if len(picks_out) < 3:
            return None
    if len(reply) < 12:
        reply = "Ниже — точки из каталога по вашему запросу; откройте карту и карточки бань для контактов."
    if len(reply) > 2800:
        reply = reply[:2797] + "…"
    return {
        "reply": reply,
        "stub": False,
        "llm": True,
        "model": model,
        "recommendations": picks_out,
        "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
    }


def _assistant_filter_hint(body: GdeparAssistantIn) -> str:
    hint_parts: list[str] = []
    if body.city and str(body.city).strip():
        hint_parts.append(f"город: {str(body.city).strip()[:80]}")
    if body.heat and str(body.heat).strip() and str(body.heat).strip().lower() != "all":
        hint_parts.append(f"нагрев: {str(body.heat).strip()[:20]}")
    if body.seen_spot_ids:
        tail = body.seen_spot_ids[:24]
        suf = "…" if len(body.seen_spot_ids) > 24 else ""
        hint_parts.append(f"уже смотрели на устройстве (id): {','.join(str(x) for x in tail)}{suf}")
    return (" (" + "; ".join(hint_parts) + " — подстроим подбор, когда подключим модель.)") if hint_parts else ""


async def _assistant_complete_payload(request: Request, body: GdeparAssistantIn) -> tuple[dict, int]:
    """Собрать финальный JSON-ответ помощника (кэш, RL, LLM или заглушка)."""
    t0 = time.perf_counter()
    msg = body.message.strip()
    filter_hint = _assistant_filter_hint(body)

    if not msg:
        payload = {
            "reply": "Напишите пару слов: город, дровяная или электро, пожелания по атмосфере — так проще подсказать направление.",
            "stub": True,
            "empty": True,
            "llm_rollout": False,
            "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
        }
        _log_assistant_timing(
            request, route="assistant", elapsed_ms=(time.perf_counter() - t0) * 1000, page=body.page, payload=payload
        )
        return payload, 200

    client_fp = _assistant_client_fp(request)
    llm_on = _assistant_llm_rollout_for_client_today(client_fp)

    if _assistant_message_toxic_blocked(msg):
        if not await _assistant_rate_allows(request):
            _assistant_logger.info("stub rate_limited client_fp=%s page=%s", client_fp, body.page or "-")
            payload = {
                "reply": "Слишком частые запросы. Подождите минуту и попробуйте снова.",
                "stub": True,
                "rate_limited": True,
                "llm_rollout": llm_on,
                "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
            }
            _log_assistant_timing(
                request, route="assistant", elapsed_ms=(time.perf_counter() - t0) * 1000, page=body.page, payload=payload
            )
            return payload, 429
        _assistant_logger.info("stub toxic_blocked client_fp=%s page=%s", client_fp, body.page or "-")
        payload = {
            "reply": (
                "Сообщение не проходит фильтр вежливости для публичного помощника. "
                "Переформулируйте запрос нейтрально (город, нагрев, пожелания) — так мы сможем подсказать по каталогу."
            ),
            "stub": True,
            "toxic_blocked": True,
            "llm_rollout": llm_on,
            "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
        }
        _log_assistant_timing(
            request, route="assistant", elapsed_ms=(time.perf_counter() - t0) * 1000, page=body.page, payload=payload
        )
        return payload, 200

    if _assistant_message_likely_spam(msg):
        if not await _assistant_rate_allows(request):
            _assistant_logger.info("stub rate_limited client_fp=%s page=%s", client_fp, body.page or "-")
            payload = {
                "reply": "Слишком частые запросы. Подождите минуту и попробуйте снова.",
                "stub": True,
                "rate_limited": True,
                "llm_rollout": llm_on,
                "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
            }
            _log_assistant_timing(
                request, route="assistant", elapsed_ms=(time.perf_counter() - t0) * 1000, page=body.page, payload=payload
            )
            return payload, 429
        _assistant_logger.info("stub spam_blocked client_fp=%s page=%s", client_fp, body.page or "-")
        payload = {
            "reply": (
                "Сообщение похоже на автоматический набор символов или перегружено ссылками. "
                "Напишите обычным текстом, что ищете по городу и бане — так помощник сможет ответить по каталогу."
            ),
            "stub": True,
            "spam_blocked": True,
            "llm_rollout": llm_on,
            "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
        }
        _log_assistant_timing(
            request, route="assistant", elapsed_ms=(time.perf_counter() - t0) * 1000, page=body.page, payload=payload
        )
        return payload, 200

    cache_key = _assistant_cache_key(
        msg,
        body.page,
        body.city,
        body.heat,
        llm_mode=llm_on,
        seen_spot_ids=body.seen_spot_ids,
    )
    cached = await _assistant_cache_get(cache_key)
    if cached is not None:
        out = dict(cached)
        if not out.get("disclaimer"):
            out["disclaimer"] = _GDEPAR_TRANSPARENCY_NOTE
        out["cached"] = True
        out["llm_rollout"] = llm_on
        _log_assistant_cache_hit(request, body.page)
        _log_assistant_timing(
            request, route="assistant", elapsed_ms=(time.perf_counter() - t0) * 1000, page=body.page, payload=out
        )
        return out, 200

    if not await _assistant_rate_allows(request):
        _assistant_logger.info("stub rate_limited client_fp=%s page=%s", client_fp, body.page or "-")
        payload = {
            "reply": "Слишком частые запросы. Подождите минуту и попробуйте снова.",
            "stub": True,
            "rate_limited": True,
            "llm_rollout": llm_on,
            "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
        }
        _log_assistant_timing(
            request, route="assistant", elapsed_ms=(time.perf_counter() - t0) * 1000, page=body.page, payload=payload
        )
        return payload, 429

    payload: dict | None = None
    if llm_on:
        payload = await _assistant_llm_reply_payload(msg, body.city, body.heat, body.seen_spot_ids)
        if payload:
            picks_n = len(payload.get("recommendations") or [])
            _assistant_logger.info(
                "assistant_llm_ok len=%s len_bucket=%s client_fp=%s picks=%s",
                len(msg),
                _assistant_len_bucket(len(msg)),
                client_fp,
                picks_n,
            )
    if payload is None:
        _log_assistant_stub_request(request, msg, body.page)
        payload = _assistant_stub_payload(filter_hint)
        stub_recs = await _assistant_stub_recommendations(
            body.city, body.heat, body.seen_spot_ids, min_picks=3, fetch_cap=48
        )
        if stub_recs:
            payload = dict(payload)
            payload["recommendations"] = stub_recs
            prev = str(payload.get("reply") or "")
            payload["reply"] = (
                prev + " Ниже — несколько точек из каталога по текущим фильтрам (подбор без ИИ)."
            )

    payload["llm_rollout"] = llm_on
    await _assistant_cache_set(cache_key, payload)
    _log_assistant_timing(
        request, route="assistant", elapsed_ms=(time.perf_counter() - t0) * 1000, page=body.page, payload=payload
    )
    return payload, 200


def _assistant_stub_reply_chunks(text: str, size: int = 28) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


async def _assistant_sse_event_stream(request: Request, body: GdeparAssistantIn) -> AsyncIterator[bytes]:
    t0 = time.perf_counter()
    msg = body.message.strip()
    filter_hint = _assistant_filter_hint(body)
    if not msg:
        payload, _ = await _assistant_complete_payload(request, body)
        yield _assistant_sse_bytes("done", payload)
        return

    client_fp = _assistant_client_fp(request)
    llm_on = _assistant_llm_rollout_for_client_today(client_fp)

    if _assistant_message_toxic_blocked(msg) or _assistant_message_likely_spam(msg):
        payload, status = await _assistant_complete_payload(request, body)
        yield _assistant_sse_bytes("done", payload)
        return

    cache_key = _assistant_cache_key(
        msg, body.page, body.city, body.heat, llm_mode=llm_on, seen_spot_ids=body.seen_spot_ids
    )
    cached = await _assistant_cache_get(cache_key)
    if cached is not None:
        out = dict(cached)
        if not out.get("disclaimer"):
            out["disclaimer"] = _GDEPAR_TRANSPARENCY_NOTE
        out["cached"] = True
        out["llm_rollout"] = llm_on
        _log_assistant_cache_hit(request, body.page)
        yield _assistant_sse_bytes("done", out)
        return

    if not await _assistant_rate_allows(request):
        yield _assistant_sse_bytes(
            "done",
            {
                "reply": "Слишком частые запросы. Подождите минуту и попробуйте снова.",
                "stub": True,
                "rate_limited": True,
                "llm_rollout": llm_on,
                "disclaimer": _GDEPAR_TRANSPARENCY_NOTE,
            },
        )
        return

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = _assistant_llm_model()
    payload: dict | None = None
    streamed_reply = False
    if llm_on and api_key:
        composed = await _assistant_llm_compose_user_message(
            msg, body.city, body.heat, body.seen_spot_ids, streaming=True
        )
        if composed:
            user, allowed_ids, id_slug = composed
            accumulated = ""
            sent = 0
            async for delta in _openrouter_chat_stream_deltas(
                api_key=api_key, model=model, user=user, title="Gdepar assistant stream"
            ):
                accumulated += delta
                chunk, sent = _assistant_stream_reply_delta(accumulated, sent)
                if chunk:
                    streamed_reply = True
                    yield _assistant_sse_bytes("delta", {"text": chunk})
            payload = await _assistant_llm_payload_from_stream_body(
                accumulated, allowed_ids, id_slug, body.city, body.heat, body.seen_spot_ids, model
            )
            if payload:
                _assistant_logger.info(
                    "assistant_llm_stream_ok len=%s client_fp=%s picks=%s",
                    len(msg),
                    client_fp,
                    len(payload.get("recommendations") or []),
                )

    if payload is None:
        if llm_on and api_key:
            payload = await _assistant_llm_reply_payload(msg, body.city, body.heat, body.seen_spot_ids)
        if payload is None:
            _log_assistant_stub_request(request, msg, body.page)
            payload = _assistant_stub_payload(filter_hint)
            stub_recs = await _assistant_stub_recommendations(
                body.city, body.heat, body.seen_spot_ids, min_picks=3, fetch_cap=48
            )
            if stub_recs:
                payload = dict(payload)
                payload["recommendations"] = stub_recs
                prev = str(payload.get("reply") or "")
                payload["reply"] = (
                    prev + " Ниже — несколько точек из каталога по текущим фильтрам (подбор без ИИ)."
                )

    if payload is not None and not streamed_reply:
        reply = str(payload.get("reply") or "")
        for chunk in _assistant_stub_reply_chunks(reply):
            yield _assistant_sse_bytes("delta", {"text": chunk})

    payload["llm_rollout"] = llm_on
    await _assistant_cache_set(cache_key, payload)
    _log_assistant_timing(
        request, route="assistant/stream", elapsed_ms=(time.perf_counter() - t0) * 1000, page=body.page, payload=payload
    )
    yield _assistant_sse_bytes("done", payload)


def _gdepar_health_payload() -> dict:
    return {
        "status": "ok",
        "asset_version": GDEPAR_ASSET_VERSION,
        "metrika_id_set": bool(YANDEX_METRIKA_ID),
        "assistant": {
            "llm_flag": _assistant_llm_enabled(),
            "llm_pct": _assistant_llm_percent(),
            "openrouter_key_set": bool(os.getenv("OPENROUTER_API_KEY", "").strip()),
            "cache_seconds": _assistant_cache_ttl_seconds(),
            "rl_per_min": int(os.getenv("GDEPAR_ASSISTANT_RL_PER_MIN", "24") or 24),
        },
        "popup_summary": {
            "llm_flag": _popup_summary_llm_enabled(),
            "llm_pct": _popup_summary_llm_percent(),
        },
    }


async def _fetch_banya_spots(
    city: str | None,
    heating: str,
    visited_only: bool,
) -> list[BanyaSpot]:
    async with async_session() as session:
        stmt = select(BanyaSpot).order_by(BanyaSpot.city, BanyaSpot.title)
        stmt = _apply_banya_filters(stmt, city, heating, visited_only)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def _distinct_cities_published() -> list[str]:
    async with async_session() as session:
        stmt = (
            select(BanyaSpot.city)
            .where(BanyaSpot.status == "published")
            .distinct()
            .order_by(BanyaSpot.city)
        )
        rows = await session.execute(stmt)
        return [r[0] for r in rows.fetchall() if r[0]]


_BANYA_SLUG_PATH = re.compile(r"^[\w\-]{1,220}$", re.UNICODE)


async def _fetch_spot_by_slug_published(slug: str) -> BanyaSpot | None:
    async with async_session() as session:
        stmt = select(BanyaSpot).where(BanyaSpot.slug == slug, BanyaSpot.status == "published")
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def _published_spot_slugs_for_sitemap() -> list[tuple[str, datetime | None]]:
    async with async_session() as session:
        stmt = (
            select(BanyaSpot.slug, BanyaSpot.updated_at)
            .where(BanyaSpot.status == "published", BanyaSpot.slug.isnot(None))
            .where(BanyaSpot.slug != "")
            .order_by(BanyaSpot.slug)
        )
        rows = (await session.execute(stmt)).all()
        out: list[tuple[str, datetime | None]] = []
        for slug, u_at in rows:
            if not slug:
                continue
            s = str(slug).strip()
            if s:
                out.append((s, u_at))
        return out


def _xml_escape_loc(url: str) -> str:
    return url.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _sitemap_lastmod_day(dt: datetime | None) -> str:
    if not dt:
        return ""
    try:
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


@app.head("/")
async def home_head():
    """HEAD для проверок (curl -I, мониторинг); без тела."""
    return Response(status_code=200, headers=_html_public_page_headers(f"{CANONICAL_BASE_URL}/"))


@app.get("/map/", include_in_schema=False)
async def map_trailing_slash_redirect():
    return RedirectResponse(url="/map", status_code=301)


@app.head("/map/", include_in_schema=False)
async def map_trailing_slash_redirect_head():
    return RedirectResponse(url="/map", status_code=301)


@app.head("/map")
async def map_head(
    city: str | None = Query(None),
    heating: str = Query("all"),
    visited: str | None = Query(None),
    _spot: int | None = Query(None, ge=1),
):
    visited_only = visited == "1"
    city_n = _normalize_city_param(city)
    canon_map = map_canonical_url(city_n, heating or "all", visited_only)
    return Response(status_code=200, headers=_html_public_page_headers(canon_map))


@app.get("/robots.txt")
async def robots_txt():
    """Индексация публичных страниц; админка и служебные пути не нужны в поиске."""
    root = CANONICAL_BASE_URL
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "\n"
        f"Sitemap: {root}/sitemap.xml\n"
    )
    return Response(content=body, media_type="text/plain; charset=utf-8", headers=_SEO_STATIC_CACHE)


@app.get("/sitemap.xml")
async def sitemap_xml():
    """Карта сайта: главная, карта бань и опубликованные карточки /banya/{slug}."""
    root = CANONICAL_BASE_URL
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <url><loc>%s</loc><changefreq>daily</changefreq><priority>1.0</priority></url>"
        % _xml_escape_loc(f"{root}/"),
        "  <url><loc>%s</loc><changefreq>daily</changefreq><priority>0.9</priority></url>"
        % _xml_escape_loc(f"{root}/map"),
    ]
    for slug, u_at in await _published_spot_slugs_for_sitemap():
        loc = _xml_escape_loc(f"{root}/banya/{slug}")
        lm = _sitemap_lastmod_day(u_at)
        if lm:
            lines.append(
                f"  <url><loc>{loc}</loc><lastmod>{lm}</lastmod>"
                "<changefreq>weekly</changefreq><priority>0.75</priority></url>"
            )
        else:
            lines.append(
                f"  <url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>0.75</priority></url>"
            )
    lines.append("</urlset>")
    xml = "\n".join(lines) + "\n"
    return Response(content=xml, media_type="application/xml; charset=utf-8", headers=_SEO_STATIC_CACHE)


@app.get("/")
async def home(request: Request):
    async with async_session() as session:
        stmt = (
            select(PostDraft)
            .where(PostDraft.persona_key == "gdepar", PostDraft.status == "published")
            .order_by(desc(PostDraft.created_at))
            .limit(3)
        )
        result = await session.execute(stmt)
        posts = list(result.scalars().all())

    # Точки и города для карты-виджета на главной (без фильтров: все опубликованные).
    map_spots = await _fetch_banya_spots(city=None, heating="all", visited_only=False)
    map_spots_data = [_spot_to_dict(s) for s in map_spots]
    map_city_options = _city_options_for_ui(await _distinct_cities_published())

    return templates.TemplateResponse(
        request,
        "gdepar.html",
        {
            "request": request,
            "posts": posts,
            "canonical_host": CANONICAL_HOST,
            "site_title": "Где Пар",
            "site_tagline": "Дровяные бани, парение, тёплое братство",
            "map_spots_data": map_spots_data,
            "map_spots_count": len(map_spots_data),
            "map_city_options": map_city_options,
            "filter_city": "",
            "asset_version": GDEPAR_ASSET_VERSION,
            "metrika_id": YANDEX_METRIKA_ID,
            "metrika_page": "home",
            "canonical_base_url": CANONICAL_BASE_URL,
            "canonical_page_url": f"{CANONICAL_BASE_URL}/",
            "og_title": "Где Пар — дровяные бани, парение, тёплое братство",
            "og_description": (
                "Где Пар — путеводитель по дровяным баням и каменкам. "
                "Где жарко, где парят, где встречают как своего."
            ),
            "og_image_url": _gdepar_share_image_url(),
            "og_image_alt": "Где Пар — путеводитель по дровяным баням и каменкам",
            "schema_org_json": gdepar_schema_org_markup(CANONICAL_BASE_URL),
        },
        headers=_html_public_page_headers(f"{CANONICAL_BASE_URL}/"),
    )


@app.get("/map")
async def map_page(
    request: Request,
    city: str | None = Query(None, description="Фильтр по городу"),
    heating: str = Query("all", description="wood|electric|mixed|unknown|all"),
    visited: str | None = Query(None, description="1 — только с личным визитом"),
    spot: int | None = Query(
        None,
        ge=1,
        description="Подсветка точки на карте; сохраняется в форме фильтров как скрытое поле",
    ),
):
    visited_only = visited == "1"
    city_n = _normalize_city_param(city)
    spots = await _fetch_banya_spots(city=city_n, heating=heating or "all", visited_only=visited_only)
    city_options = _city_options_for_ui(await _distinct_cities_published())
    spots_data = [_spot_to_dict(s) for s in spots]
    canon_map = map_canonical_url(city_n, heating or "all", visited_only)

    return templates.TemplateResponse(
        request,
        "gdepar_map.html",
        {
            "request": request,
            "canonical_host": CANONICAL_HOST,
            "site_title": "Где Пар",
            "site_tagline": "Дровяные бани, парение, тёплое братство",
            "spots_data": spots_data,
            "city_options": city_options,
            "filter_city": city_n or "",
            "filter_heating": heating or "all",
            "filter_visited": visited_only,
            "filter_spot_id": spot,
            "asset_version": GDEPAR_ASSET_VERSION,
            "metrika_id": YANDEX_METRIKA_ID,
            "metrika_page": "map",
            "canonical_base_url": CANONICAL_BASE_URL,
            "canonical_page_url": canon_map,
            "og_title": "Карта бань — Где Пар",
            "og_description": (
                "Карта общественных и дровяных бань — Где Пар. "
                "Фильтры по городу, типу нагрева, личным визитам."
            ),
            "og_image_url": _gdepar_share_image_url(),
            "og_image_alt": "Где Пар — карта дровяных и общественных бань",
            "map_schema_org_json": gdepar_map_schema_org_markup(CANONICAL_BASE_URL, canon_map),
        },
        headers=_html_public_page_headers(canon_map),
    )


@app.get("/banya", include_in_schema=False)
async def banya_list_redirect():
    """Без slug ведём на карту (частая опечатка / устаревшие ссылки)."""
    return RedirectResponse(url="/map", status_code=301)


@app.head("/banya", include_in_schema=False)
async def banya_list_redirect_head():
    return RedirectResponse(url="/map", status_code=301)


@app.get("/banya/{slug}/", include_in_schema=False)
async def banya_spot_trailing_slash_redirect_get(slug: str):
    """Канонический URL без завершающего слэша (дубли в поиске)."""
    if not _BANYA_SLUG_PATH.match(slug):
        raise HTTPException(status_code=404, detail="Not Found")
    row = await _fetch_spot_by_slug_published(slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return RedirectResponse(url=f"/banya/{slug}", status_code=301)


@app.head("/banya/{slug}/", include_in_schema=False)
async def banya_spot_trailing_slash_redirect_head(slug: str):
    if not _BANYA_SLUG_PATH.match(slug):
        return Response(status_code=404)
    row = await _fetch_spot_by_slug_published(slug)
    if row is None:
        return Response(status_code=404)
    return RedirectResponse(url=f"/banya/{slug}", status_code=301)


@app.head("/banya/{slug}")
async def banya_spot_head(request: Request, slug: str):
    if not _BANYA_SLUG_PATH.match(slug):
        return Response(status_code=404)
    row = await _fetch_spot_by_slug_published(slug)
    if row is None:
        return Response(status_code=404)
    page_url = f"{CANONICAL_BASE_URL}/banya/{slug}"
    if _not_modified_since_client_header(
        request.headers.get("if-modified-since"),
        row.updated_at,
    ):
        return Response(status_code=304, headers=_spot_page_http_headers(row.updated_at, canonical_page_url=page_url))
    return Response(status_code=200, headers=_spot_page_http_headers(row.updated_at, canonical_page_url=page_url))


@app.get("/banya/{slug}")
async def banya_spot_page(request: Request, slug: str):
    if not _BANYA_SLUG_PATH.match(slug):
        raise HTTPException(status_code=404, detail="Not Found")
    spot = await _fetch_spot_by_slug_published(slug)
    if spot is None:
        raise HTTPException(status_code=404, detail="Not Found")
    page_url = f"{CANONICAL_BASE_URL}/banya/{slug}"
    if _not_modified_since_client_header(
        request.headers.get("if-modified-since"),
        spot.updated_at,
    ):
        return Response(status_code=304, headers=_spot_page_http_headers(spot.updated_at, canonical_page_url=page_url))
    spot_d = _spot_to_dict(spot)
    spot_og_image = _spot_og_image_url(spot_d.get("cover_url"), CANONICAL_BASE_URL)
    default_og = f"{CANONICAL_BASE_URL.rstrip('/')}/static/gdepar/logos/03-drop.svg"
    show_spot_cover_hero = bool(spot_d.get("cover_url")) and spot_og_image != default_og
    sid = spot_d.get("id")
    spot_reviews: list[dict] = []
    if isinstance(sid, int):
        spot_reviews = await _approved_reviews_for_spot_page(sid, 12)
    desc = (spot_d.get("description") or "").strip()
    if not desc:
        desc = f"{spot_d.get('title') or 'Баня'} — на карте «Где Пар»."
    og_desc = desc[:300] if len(desc) > 300 else desc
    return templates.TemplateResponse(
        request,
        "gdepar_spot.html",
        {
            "request": request,
            "canonical_host": CANONICAL_HOST,
            "site_title": "Где Пар",
            "site_tagline": "Дровяные бани, парение, тёплое братство",
            "spot": spot_d,
            "asset_version": GDEPAR_ASSET_VERSION,
            "metrika_id": YANDEX_METRIKA_ID,
            "metrika_page": "spot",
            "canonical_base_url": CANONICAL_BASE_URL,
            "canonical_page_url": page_url,
            "nav_active": "map",
            "og_title": f"{spot_d.get('title') or 'Баня'} — Где Пар",
            "og_description": og_desc,
            "spot_og_image": spot_og_image,
            "show_spot_cover_hero": show_spot_cover_hero,
            "spot_schema_org_json": gdepar_spot_schema_org_markup(
                CANONICAL_BASE_URL,
                page_url,
                spot_d,
                spot_reviews or None,
                spot.updated_at,
                spot.created_at,
                spot_og_image,
            ),
            "spot_modified_iso": _page_modified_iso(spot.updated_at),
            "spot_created_iso": _page_modified_iso(spot.created_at),
            "spot_reviews": spot_reviews,
        },
        headers=_spot_page_http_headers(spot.updated_at, canonical_page_url=page_url),
    )


@app.get("/api/banya/spots")
async def api_banya_spots(
    city: str | None = None,
    heating: str = "all",
    visited: str | None = None,
):
    """JSON для карты / внешних клиентов (те же фильтры, что у /map)."""
    visited_only = visited == "1"
    city_n = _normalize_city_param(city)
    spots = await _fetch_banya_spots(city=city_n, heating=heating or "all", visited_only=visited_only)
    return JSONResponse([_spot_to_dict(s) for s in spots])


@app.get("/api/banya/reviews/{spot_id}")
async def api_banya_reviews(spot_id: int, limit: int = 5):
    """Совместимость: только список одобренных отзывов (без сводки). Для UI карты см. /api/banya/reviews-block/."""
    limit = max(1, min(20, limit))
    async with async_session() as session:
        stmt = (
            select(BanyaReview)
            .where(
                BanyaReview.spot_id == spot_id,
                BanyaReview.status == "approved",
            )
            .order_by(BanyaReview.id.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        reviews = list(result.scalars().all())
    return JSONResponse([
        {
            "id": rv.id,
            "author": rv.author or "Гость",
            "rating": rv.rating,
            "text": rv.text or "",
            "source": rv.source,
        }
        for rv in reviews
    ])


def _popup_summary_llm_enabled() -> bool:
    if not os.getenv("OPENROUTER_API_KEY", "").strip():
        return False
    return os.getenv("GDEPAR_POPUP_SUMMARY_LLM", "").strip().lower() in ("1", "true", "yes", "on")


def _popup_summary_llm_percent() -> int:
    """Доля запросов саммари (на spot_id за календарный день UTC), где пробуем LLM; 0–100."""
    try:
        return max(0, min(100, int(os.getenv("GDEPAR_POPUP_SUMMARY_LLM_PCT", "100"))))
    except ValueError:
        return 100


def _popup_summary_llm_selected_for_spot_today(spot_id: int) -> bool:
    """Детерминированный A/B: один и тот же spot в течение суток UTC стабильно попадает или нет в ветку LLM."""
    if not _popup_summary_llm_enabled():
        return False
    pct = _popup_summary_llm_percent()
    if pct <= 0:
        return False
    if pct >= 100:
        return True
    day = datetime.now(timezone.utc).date().isoformat()
    h = int(hashlib.sha256(f"{spot_id}|{day}".encode("utf-8")).hexdigest(), 16)
    return (h % 100) < pct


def _popup_summary_llm_model() -> str:
    return (os.getenv("GDEPAR_POPUP_SUMMARY_MODEL") or os.getenv("GDEPAR_ASSISTANT_MODEL") or "openai/gpt-4o-mini").strip()


def _popup_summary_llm_timeout_sec() -> float:
    try:
        return max(5.0, min(60.0, float(os.getenv("GDEPAR_POPUP_SUMMARY_LLM_TIMEOUT", "18"))))
    except ValueError:
        return 18.0


def _popup_summary_llm_max_tokens() -> int:
    try:
        return max(120, min(900, int(os.getenv("GDEPAR_POPUP_SUMMARY_LLM_MAX_TOKENS", "420"))))
    except ValueError:
        return 420


def _reviews_bullets_for_summary_llm(reviews: list[BanyaReview], cap: int = 18) -> str:
    lines: list[str] = []
    for r in reviews[:cap]:
        txt = (r.text or "").replace("\n", " ").strip()
        if len(txt) > 380:
            txt = txt[:377] + "…"
        ra = f"оценка {r.rating}" if r.rating is not None else "без оценки"
        who = (r.author or "гость").strip()[:48]
        if not txt and r.rating is None:
            continue
        lines.append(f"- ({ra}, {who}): {txt or '—'}")
    return "\n".join(lines)


async def _popup_summary_llm_parts(reviews: list[BanyaReview], spot_id: int) -> dict | None:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key or not reviews:
        return None
    bullets = _reviews_bullets_for_summary_llm(reviews)
    if not bullets.strip():
        return None
    user = (
        f"Каталог: одна баня, spot_id={spot_id}. Ниже одобренные отзывы посетителей.\n"
        "Сделай краткую сводку по-русски только на основе этих текстов; "
        "не выдумывай факты, которых нет в отзывах.\n"
        "Не вставляй длинные цитаты подряд и не упоминай Яндекс.Карты.\n\n"
        f"Отзывы:\n{bullets}\n\n"
        'Верни один JSON UTF-8 без markdown: '
        '{"intro":"1–2 предложения общий вывод",'
        '"bullets":["тезис до 120 символов","ещё тезис"]} '
        "(bullets: 3–5 пунктов, без кавычек из отзывов)."
    )
    model = _popup_summary_llm_model()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": f"{CANONICAL_BASE_URL}/",
                    "X-Title": "Gdepar popup summary",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Ты редактор кратких сводок отзывов для gdepar.ru. "
                                "Пишешь только по переданным отзывам; без markdown и без длинных цитат."
                            ),
                        },
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                    "max_tokens": _popup_summary_llm_max_tokens(),
                },
                timeout=_popup_summary_llm_timeout_sec(),
            )
    except Exception as exc:
        _assistant_logger.warning("popup_summary_llm_http_error %s", type(exc).__name__)
        return None
    if resp.status_code != 200:
        _assistant_logger.warning("popup_summary_llm_status=%s", resp.status_code)
        return None
    try:
        data = resp.json()
        content = (data["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return None
    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\s*", "", content)
        content = re.sub(r"\s*```\s*$", "", content).strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        _assistant_logger.info("popup_summary_llm_json_decode")
        return None
    parts = _popup_summary_parts_from_llm(parsed, reviews)
    if not parts:
        return None
    _assistant_logger.info("popup_summary_llm_ok spot_id=%s model=%s", spot_id, model)
    return parts


@app.get("/api/banya/reviews-block/{spot_id}")
async def api_banya_reviews_block(
    spot_id: int,
    limit: int = 5,
    include_summary: int = Query(
        0,
        ge=0,
        le=1,
        description="1 — сводка (кнопка «Дай саммари»); 0 — только список отзывов",
    ),
):
    """Отзывы для попапа: список отдельно; сводка — запросом с include_summary=1."""
    list_limit = max(1, min(15, limit))
    order_col = func.coalesce(BanyaReview.published_at, BanyaReview.fetched_at)
    async with async_session() as session:
        if not include_summary:
            stmt = (
                select(BanyaReview)
                .where(
                    BanyaReview.spot_id == spot_id,
                    BanyaReview.status == "approved",
                )
                .order_by(desc(order_col), desc(BanyaReview.id))
                .limit(list_limit)
            )
            result = await session.execute(stmt)
            reviews = list(result.scalars().all())
            return JSONResponse(_reviews_list_payload(reviews, list_limit))

        sample_limit = min(50, max(24, list_limit * 4))
        stmt = (
            select(BanyaReview)
            .where(
                BanyaReview.spot_id == spot_id,
                BanyaReview.status == "approved",
            )
            .order_by(desc(order_col), desc(BanyaReview.id))
            .limit(sample_limit)
        )
        result = await session.execute(stmt)
        reviews = list(result.scalars().all())
    payload = _build_reviews_block_payload(reviews, list_limit)
    payload["summary_source"] = "heuristic"
    if _popup_summary_llm_selected_for_spot_today(spot_id) and reviews:
        llm_parts = await _popup_summary_llm_parts(reviews, spot_id)
        if llm_parts:
            _apply_summary_parts_to_payload(payload, llm_parts)
            payload["summary_source"] = "llm"
    return JSONResponse(payload)


@app.get("/api/gdepar/health")
async def api_gdepar_health():
    """Проверка живости процесса (балансировщик, systemd, Docker)."""
    return JSONResponse(_gdepar_health_payload())


@app.head("/api/gdepar/health")
async def api_gdepar_health_head():
    return Response(status_code=200)


class GdeparAssistantIn(BaseModel):
    message: str = Field(default="", max_length=2000)
    page: Literal["home", "map", "spot"] | None = None
    city: str | None = Field(default=None, max_length=120)
    heat: str | None = Field(default=None, max_length=24)
    seen_spot_ids: list[int] | None = None

    @model_validator(mode="after")
    def _normalize_seen_spot_ids(self) -> Self:
        raw = self.seen_spot_ids
        if not raw:
            self.seen_spot_ids = None
            return self
        out: list[int] = []
        for x in raw:
            try:
                i = int(x)
                if i > 0 and i not in out:
                    out.append(i)
                if len(out) >= 48:
                    break
            except (TypeError, ValueError):
                continue
        self.seen_spot_ids = out or None
        return self


@app.post("/api/gdepar/assistant")
async def api_gdepar_assistant(request: Request, body: GdeparAssistantIn):
    """Помощник: заглушка, опционально LLM (GDEPAR_ASSISTANT_LLM), кэш (GDEPAR_ASSISTANT_CACHE_SECONDS)."""
    t0 = time.perf_counter()
    payload, status = await _assistant_complete_payload(request, body)
    headers = {"X-Gdepar-Response-Ms": str(int((time.perf_counter() - t0) * 1000))}
    return JSONResponse(payload, status_code=status, headers=headers)


@app.post("/api/gdepar/assistant/stream")
async def api_gdepar_assistant_stream(request: Request, body: GdeparAssistantIn):
    """SSE-стрим: event delta {text}, затем event done с полным JSON (как /assistant)."""
    return StreamingResponse(
        _assistant_sse_event_stream(request, body),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    port = int(os.getenv("GDEPAR_WEB_PORT", "8001"))
    uvicorn.run(app, host="127.0.0.1", port=port)
