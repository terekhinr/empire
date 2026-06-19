"""Сайт «На пенсию НИКОГДА» (neverretire.ru).

Маршруты:
  /            — главная (hero, манифест-выжимка, превью книги, последние статьи, видео, CTA)
  /book        — оглавление книги
  /book/<slug> — глава книги
  /buy         — страница покупки (заглушка до ЮKassa)
  /articles    — лента опубликованных статей
  /articles/<id> — отдельная статья
  /videos      — видео-галерея (YouTube embeds)
  /about       — о проекте и контакты
  /api/health  — health + metrika_id_set
  POST /api/health/ingest — Health Connect webhook (Lifesum nutrition, weight)
  POST /api/pension/waitlist — email pre-launch
  /robots.txt  — индексация
  /sitemap.xml — карта сайта

Использует контент из:
  • empire.db (post_drafts persona_key=pension, published)
  • data/book/napensiyu_nikogda.json
  • data/site/videos.json
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from empire_models import DATABASE_URL, PostDraft
from health_connect_ingest import ingest_health_connect_payload
from pension_metrics import append_waitlist_email, waitlist_count

BASE_DIR = Path(__file__).parent
CANONICAL_HOST = os.getenv("EMPIRE_CANONICAL_HOST", "neverretire.ru").strip() or "neverretire.ru"
SITE_TITLE = "На пенсию НИКОГДА"
SITE_TAGLINE = "Манифест антихрупкости и вечного движения"

_raw_metrika = os.getenv("YANDEX_METRIKA_ID", "").strip()
YANDEX_METRIKA_ID = _raw_metrika if _raw_metrika.isdigit() else ""

_DEFAULT_PENSION_TG_URL = "https://t.me/pensiya_nikogda"


def _env_nonempty(key: str, default: str) -> str:
    """os.getenv default не срабатывает, если в .env ключ задан пустым."""
    v = (os.getenv(key) or "").strip()
    return v if v else default


PENSION_TG_URL = _env_nonempty("PENSION_TG_URL", _DEFAULT_PENSION_TG_URL)
PENSION_TG_PERSONAL_URL = _env_nonempty(
    "PENSION_TG_PERSONAL_URL", "https://t.me/iosif_boroda"
)
PENSION_VK_URL = os.getenv("PENSION_VK_URL", "").strip()
PENSION_DZEN_URL = os.getenv("PENSION_DZEN_URL", "").strip()
PENSION_YOUTUBE_URL = os.getenv(
    "PENSION_YOUTUBE_URL",
    "https://www.youtube.com/channel/UC-XdhgaT-gXZPJpODed8Ksw",
).strip()
BOOK_PDF_PRICE_RUB = int(os.getenv("PENSION_BOOK_PRICE_RUB", "990") or "990")
HEALTH_INGEST_TOKEN = os.getenv("HEALTH_INGEST_TOKEN", "").strip()

app = FastAPI(title=SITE_TITLE, docs_url=None, redoc_url=None)

os.makedirs(BASE_DIR / "static", exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _metrika_page_for_path(path: str, *, slug: str | None = None) -> str:
    if path == "/" or path == "":
        return "home"
    if path == "/book":
        return "book_toc"
    if path.startswith("/book/") and slug:
        return f"book_chapter:{slug}"
    if path == "/buy":
        return "buy"
    if path == "/articles":
        return "articles"
    if path.startswith("/articles/"):
        return "article"
    if path == "/videos":
        return "videos"
    if path == "/about":
        return "about"
    return "other"


def _ctx(request: Request, *, metrika_page: str | None = None, **extra: Any) -> dict[str, Any]:
    """Базовый контекст шаблона."""
    path = request.url.path
    page = metrika_page or _metrika_page_for_path(path, slug=extra.get("chapter_slug"))
    return {
        "request": request,
        "site_title": SITE_TITLE,
        "site_tagline": SITE_TAGLINE,
        "canonical_host": CANONICAL_HOST,
        "year": datetime.now().year,
        "metrika_id": YANDEX_METRIKA_ID,
        "metrika_page": page,
        "pension_tg_url": PENSION_TG_URL,
        "pension_tg_personal_url": PENSION_TG_PERSONAL_URL,
        "pension_vk_url": PENSION_VK_URL,
        "pension_dzen_url": PENSION_DZEN_URL,
        "pension_youtube_url": PENSION_YOUTUBE_URL,
        "book_price_rub": BOOK_PDF_PRICE_RUB,
        **extra,
    }


async def _fetch_published_articles(limit: int = 50) -> list[PostDraft]:
    try:
        async with async_session() as session:
            stmt = (
                select(PostDraft)
                .where(PostDraft.persona_key == "pension", PostDraft.status == "published")
                .order_by(desc(PostDraft.created_at))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
    except Exception:
        return []


class WaitlistBody(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)


@app.get("/api/health")
async def api_health():
    return {
        "ok": True,
        "site": CANONICAL_HOST,
        "metrika_id_set": bool(YANDEX_METRIKA_ID),
        "waitlist_count": waitlist_count(),
    }


@app.post("/api/pension/waitlist")
async def api_pension_waitlist(body: WaitlistBody):
    email = body.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="invalid_email")
    if not append_waitlist_email(email, source="site_form"):
        raise HTTPException(status_code=400, detail="invalid_email")
    return {"ok": True, "waitlist_count": waitlist_count()}


@app.post("/api/health/ingest")
async def api_health_ingest(
    request: Request,
    x_health_token: str | None = Header(default=None, alias="X-Health-Token"),
):
    if not HEALTH_INGEST_TOKEN:
        raise HTTPException(status_code=503, detail="health_ingest_not_configured")
    if x_health_token != HEALTH_INGEST_TOKEN:
        raise HTTPException(status_code=401, detail="invalid_token")
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid_payload")
    return ingest_health_connect_payload(payload)


@app.get("/")
async def home(request: Request):
    book = _load_json(BASE_DIR / "data" / "book" / "napensiyu_nikogda.json")
    videos_cfg = _load_json(BASE_DIR / "data" / "site" / "videos.json")
    articles = await _fetch_published_articles(limit=5)

    return templates.TemplateResponse(
        request,
        "index.html",
        _ctx(
            request,
            metrika_page="home",
            book_title=book["title"],
            book_subtitle=book["subtitle"],
            book_chapters_count=len(book["chapters"]),
            videos=videos_cfg["videos"][:3],
            youtube_channel_name=videos_cfg.get("channel_name", "Иосиф Борода"),
            youtube_channel_url=videos_cfg.get("channel_url") or PENSION_YOUTUBE_URL,
            articles=articles,
            waitlist_count=waitlist_count(),
        ),
    )


@app.get("/book")
async def book_toc(request: Request):
    book = _load_json(BASE_DIR / "data" / "book" / "napensiyu_nikogda.json")
    return templates.TemplateResponse(
        request,
        "book_toc.html",
        _ctx(request, metrika_page="book_toc", book=book),
    )


@app.get("/book/{slug}")
async def book_chapter(request: Request, slug: str):
    book = _load_json(BASE_DIR / "data" / "book" / "napensiyu_nikogda.json")
    chapters = book["chapters"]

    idx = next((i for i, c in enumerate(chapters) if c["slug"] == slug), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Глава не найдена")

    return templates.TemplateResponse(
        request,
        "book_chapter.html",
        _ctx(
            request,
            metrika_page=f"book_chapter:{slug}",
            chapter_slug=slug,
            book=book,
            chapter=chapters[idx],
            prev_chapter=chapters[idx - 1] if idx > 0 else None,
            next_chapter=chapters[idx + 1] if idx + 1 < len(chapters) else None,
        ),
    )


@app.get("/buy")
async def buy_page(request: Request):
    book = _load_json(BASE_DIR / "data" / "book" / "napensiyu_nikogda.json")
    return templates.TemplateResponse(
        request,
        "buy.html",
        _ctx(
            request,
            metrika_page="buy",
            book=book,
            payments_live=os.getenv("PENSION_PAYMENTS_LIVE", "").strip() in ("1", "true", "yes"),
        ),
    )


@app.get("/articles")
async def articles_list(request: Request):
    articles = await _fetch_published_articles(limit=100)
    return templates.TemplateResponse(
        request,
        "articles.html",
        _ctx(request, metrika_page="articles", articles=articles),
    )


@app.get("/articles/{article_id}")
async def article_detail(request: Request, article_id: int):
    async with async_session() as session:
        article = await session.get(PostDraft, article_id)
        if not article or article.persona_key != "pension" or article.status != "published":
            raise HTTPException(status_code=404, detail="Статья не найдена")
    return templates.TemplateResponse(
        request,
        "article_detail.html",
        _ctx(request, metrika_page="article", article=article),
    )


@app.get("/videos")
async def videos_list(request: Request):
    videos_cfg = _load_json(BASE_DIR / "data" / "site" / "videos.json")
    return templates.TemplateResponse(
        request,
        "videos.html",
        _ctx(
            request,
            metrika_page="videos",
            channel_url=videos_cfg.get("channel_url") or PENSION_YOUTUBE_URL,
            channel_name=videos_cfg.get("channel_name", "Иосиф Борода"),
            videos=videos_cfg["videos"],
        ),
    )


@app.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(
        request, "about.html", _ctx(request, metrika_page="about")
    )


@app.get("/rss/pension.xml")
async def pension_rss_feed():
    """RSS для Яндекс.Дзена «На пенсию НИКОГДА» (автообновление при approve)."""
    rel = os.getenv("EMPIRE_DZEN_RSS_PENSION_PATH", "media/rss_pension.xml").lstrip("/")
    path = BASE_DIR / rel
    if not path.is_file():
        raise HTTPException(status_code=404, detail="rss_not_generated")
    return Response(
        content=path.read_text(encoding="utf-8"),
        media_type="application/rss+xml; charset=utf-8",
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return (
        f"User-agent: *\nAllow: /\nAllow: /rss/\n"
        f"Sitemap: https://{CANONICAL_HOST}/sitemap.xml\n"
    )


@app.get("/sitemap.xml")
async def sitemap():
    book = _load_json(BASE_DIR / "data" / "book" / "napensiyu_nikogda.json")
    articles = await _fetch_published_articles(limit=200)

    urls: list[str] = [
        f"https://{CANONICAL_HOST}/",
        f"https://{CANONICAL_HOST}/book",
        f"https://{CANONICAL_HOST}/buy",
        f"https://{CANONICAL_HOST}/articles",
        f"https://{CANONICAL_HOST}/videos",
        f"https://{CANONICAL_HOST}/about",
    ]
    urls.extend(f"https://{CANONICAL_HOST}/book/{c['slug']}" for c in book["chapters"])
    urls.extend(f"https://{CANONICAL_HOST}/articles/{a.id}" for a in articles)

    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        body.append(f"  <url><loc>{u}</loc></url>")
    body.append("</urlset>")
    return Response(content="\n".join(body), media_type="application/xml")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
