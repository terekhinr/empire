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
  GET  /gift         — лид-магнит (5 принципов, email → PDF)
  POST /api/pension/waitlist — email pre-launch
  POST /api/pension/gift     — email с лид-магнита /gift
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
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from empire_models import DATABASE_URL, PostDraft
from health_connect_ingest import ingest_health_connect_payload
from pension_metrics import append_waitlist_email, waitlist_count
from pension_site_feed import dedupe_pension_posts
from portfolio.web_routes import router as portfolio_router
from sauron.routes import router as sauron_router
from snegiri_kb.routes import router as snegiri_router

BASE_DIR = Path(__file__).parent
CANONICAL_HOST = os.getenv("EMPIRE_CANONICAL_HOST", "neverretire.ru").strip() or "neverretire.ru"
SNEGIRI_HOSTS = frozenset(
    h.strip().lower()
    for h in os.getenv(
        "EMPIRE_SNEGIRI_HOSTS",
        "snegirinegiri.ru,www.snegirinegiri.ru,snegirinegi.ru,www.snegirinegi.ru",
    ).split(",")
    if h.strip()
)
SNEGIRI_ROOT = BASE_DIR / "static" / "snegiri"
SNEGIRI_CANONICAL = os.getenv("EMPIRE_SNEGIRI_HOST", "snegirinegiri.ru").strip() or "snegirinegiri.ru"


def _request_host(request: Request) -> str:
    return (request.headers.get("host") or "").split(":")[0].lower()


def _is_snegiri_host(request: Request) -> bool:
    return _request_host(request) in SNEGIRI_HOSTS


def _snegiri_file(rel: str) -> FileResponse:
    path = (SNEGIRI_ROOT / rel).resolve()
    try:
        path.relative_to(SNEGIRI_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404) from exc
    if not path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(path)


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
BOOK_PDF_PRICE_RUB = int(os.getenv("PENSION_BOOK_PRICE_RUB", "149") or "149")
HEALTH_INGEST_TOKEN = os.getenv("HEALTH_INGEST_TOKEN", "").strip()

app = FastAPI(title=SITE_TITLE, docs_url=None, redoc_url=None)


@app.middleware("http")
async def hub_safe_headers(request: Request, call_next):
    """Кабинет: HEAD — пустой text/plain (не HTML/204/405 — Chrome prefetch/RST)."""
    path = request.url.path or ""
    cabinet = path.startswith("/hub") or path.startswith("/portfolio")
    if request.method == "HEAD":
        if cabinet:
            return Response(
                content=b"",
                status_code=200,
                media_type="text/plain",
                headers={"Allow": "GET, POST", "Cache-Control": "no-store, private"},
            )
        request.scope["method"] = "GET"
        response = await call_next(request)
        return Response(status_code=response.status_code, headers={"Cache-Control": "no-store"})
    response = await call_next(request)
    if cabinet:
        response.headers["Cache-Control"] = "no-store, private"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


app.include_router(snegiri_router, prefix="/api/snegiri")
app.include_router(sauron_router)
app.include_router(portfolio_router)

os.makedirs(BASE_DIR / "static", exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

import publisher.app as publisher_app

publisher_app.configure(templates)
app.include_router(publisher_app.router)

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
    if path == "/gift":
        return "gift"
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
    """Лента сайта: только published pension, без republish-дублей по заголовку."""
    try:
        async with async_session() as session:
            # Берём с запасом — после дедупа останется ≤ limit
            fetch_n = max(limit * 4, 80)
            stmt = (
                select(PostDraft)
                .where(PostDraft.persona_key == "pension", PostDraft.status == "published")
                .order_by(desc(PostDraft.created_at))
                .limit(fetch_n)
            )
            result = await session.execute(stmt)
            rows = list(result.scalars().all())
        # Сначала свежие; дедуп оставляет первую встречу → сортируем по id ASC внутри ключа
        # через повторный проход: старые id предпочтительнее при одинаковом заголовке
        rows_by_id = sorted(rows, key=lambda p: p.id or 0)
        unique = dedupe_pension_posts(rows_by_id)
        unique.sort(key=lambda p: p.created_at or p.id, reverse=True)
        return unique[:limit]
    except Exception:
        return []


class WaitlistBody(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    source: str | None = Field(default=None, max_length=64)
    utm_source: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)


class GiftBody(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    consent: bool = False
    utm_source: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)


GIFT_PDF_URL = "/static/pension/5-principles-antipension.html"


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_email(email: str) -> None:
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="invalid_email")


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
    email = _normalize_email(body.email)
    _validate_email(email)
    source = (body.source or "site_form").strip() or "site_form"
    if not append_waitlist_email(
        email,
        source=source[:64],
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
    ):
        raise HTTPException(status_code=400, detail="invalid_email")
    return {"ok": True, "waitlist_count": waitlist_count()}


@app.post("/api/pension/gift")
async def api_pension_gift(body: GiftBody):
    if not body.consent:
        raise HTTPException(status_code=400, detail="consent_required")
    email = _normalize_email(body.email)
    _validate_email(email)
    if not append_waitlist_email(
        email,
        source="gift",
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
    ):
        raise HTTPException(status_code=400, detail="invalid_email")
    return {
        "ok": True,
        "waitlist_count": waitlist_count(),
        "download_url": GIFT_PDF_URL,
    }


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


def _go_tasks_fetch(token: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Тянем задачи с localhost planning — без браузерного fetch (на ПК он зависает)."""
    import urllib.error
    import urllib.request

    tok = (token or "").strip()
    if not tok:
        return None, "no-token"
    req = urllib.request.Request(
        "http://127.0.0.1:8502/api/planning/tasks",
        headers={"X-Planning-Token": tok, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read()
        data = json.loads(raw.decode("utf-8", errors="replace"))
        tasks = data.get("tasks") if isinstance(data, dict) else None
        if not isinstance(tasks, list):
            return [], None
        return tasks, None
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return None, "auth"
        return None, f"http-{e.code}"
    except Exception as e:
        return None, str(e)[:120]


def _go_tasks_html(
    *,
    tasks: list[dict[str, Any]] | None = None,
    err: str | None = None,
    authed: bool = False,
    token: str | None = None,
) -> str:
    import html as html_lib
    from urllib.parse import quote

    items = ""
    who = ""
    if authed and tasks is not None:
        open_tasks = [
            t
            for t in tasks
            if isinstance(t, dict) and t.get("status") != "done" and not t.get("done")
        ]
        show = open_tasks[:100] if open_tasks else tasks[:100]
        who = f"Открытых: {len(open_tasks)} (всего {len(tasks)})"
        if not show:
            items = "<li>Нет задач</li>"
        else:
            bits = []
            for t in show:
                title = html_lib.escape(str(t.get("title") or f"#{t.get('id')}"))
                due = t.get("due_at") or t.get("due") or t.get("deadline") or ""
                due_s = html_lib.escape(str(due)[:16].replace("T", " ")) if due else ""
                due_html = f'<div class="due">{due_s}</div>' if due_s else ""
                bits.append(f"<li><div>{title}</div>{due_html}</li>")
            items = "".join(bits)
    err_html = html_lib.escape(err) if err else ""
    tok = (token or "").strip()
    full_ui = (
        f"/x/?reset=1&native_token={quote(tok, safe='')}&src=go-list"
        if tok
        else "/x/?reset=1&src=go-list"
    )

    if authed and tasks is not None:
        body_main = f"""
  <div class="card">
    <p style="margin:0 0 8px;color:#fff;font-size:1.15rem">{html_lib.escape(who)}</p>
    <p style="margin:0 0 10px;display:flex;flex-wrap:wrap;gap:8px">
      <a class="btn-full" href="/gym/">ЗАЛ (тренировка)</a>
      <a class="btn-full" href="/go-learn/" style="background:#4ade80;color:#052e16">ПРАКТИКУМ</a>
      <a class="btn-full" href="{html_lib.escape(full_ui)}">ПОЛНЫЙ UI (/x/)</a>
    </p>
    <form method="get" action="/go-tasks/" style="display:inline">
      <button type="submit">Обновить список</button>
    </form>
    <form method="post" action="/go-tasks/" style="display:inline;margin-left:6px">
      <input type="hidden" name="action" value="logout">
      <button type="submit" class="sec">Сменить токен</button>
    </form>
    <ul id="list">{items}</ul>
  </div>"""
    else:
        body_main = f"""
  <div class="card">
    <p><b>Главный вход.</b> Токен → список задач. На тренировку потом жми «Зал». Учёба — «Практикум».</p>
    <form method="post" action="/go-tasks/">
      <label for="tok">Токен</label>
      <input id="tok" name="token" type="password" autocomplete="off" required autofocus>
      <div id="msg">{err_html}</div>
      <button type="submit">ВОЙТИ</button>
    </form>
    <p style="margin:14px 0 0"><a href="/go/" style="color:#93c5fd">Все входы Empire</a> · <a href="/go-reset/" style="color:#fbbf24">Сброс кэша</a></p>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">
<title>Задачник</title>
<style>
  html,body{{margin:0;min-height:100%;background:#ffe600;color:#111;font-family:system-ui,sans-serif}}
  #wrap{{max-width:640px;margin:0 auto;padding:20px 16px 40px}}
  h1{{margin:0 0 8px;font-size:1.7rem}}
  .card{{background:#111;color:#ffe600;border-radius:14px;padding:18px 16px;margin:12px 0}}
  .card p,.muted{{color:#ddd;font-size:0.95rem;line-height:1.4}}
  label{{display:block;text-align:left;color:#fff;margin:8px 0 4px;font-size:0.9rem}}
  input[type=password]{{width:100%;box-sizing:border-box;padding:12px;border-radius:10px;border:2px solid #555;background:#000;color:#fff;font-size:1rem}}
  button,.btn-full{{display:inline-block;margin:8px 6px 0 0;padding:14px 18px;border:0;border-radius:10px;background:#ffe600;color:#111;font-weight:800;font-size:1.05rem;cursor:pointer;text-decoration:none}}
  button.sec{{background:#333;color:#ffe600;border:1px solid #ffe600;font-size:1rem}}
  a.btn-full{{background:#38bdf8;color:#0f172a}}
  #msg{{min-height:1.2em;color:#fbbf24;margin:8px 0;text-align:left}}
  #list{{list-style:none;padding:0;margin:12px 0 0}}
  #list li{{background:#1a1a1a;color:#fff;border-radius:10px;padding:12px 14px;margin:8px 0;text-align:left;border-left:4px solid #ffe600}}
  #list li .due{{color:#94a3b8;font-size:0.85rem;margin-top:4px}}
</style>
</head>
<body>
<div id="wrap">
  <h1>Задачник</h1>
  <p class="muted"><a href="/go/" style="color:#111;font-weight:700">Empire</a> · не открывай старую иконку /tasks/</p>
  {body_main}
</div>
<script>
try {{
  if (navigator.serviceWorker) {{
    navigator.serviceWorker.getRegistrations().then(function (rs) {{
      rs.forEach(function (r) {{ r.unregister(); }});
    }});
  }}
}} catch (e) {{}}
</script>
</body>
</html>"""


@app.get("/go")
@app.get("/go/")
async def go_hub():
    from fastapi.responses import HTMLResponse

    from go_learn import render_hub

    return HTMLResponse(
        render_hub(),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.api_route("/go-learn", methods=["GET", "POST"])
@app.api_route("/go-learn/", methods=["GET", "POST"])
async def go_learn_page(request: Request):
    """SSR Практикум (Codecademy-style) — без SPA."""
    from fastapi.responses import HTMLResponse, RedirectResponse

    from go_learn import COOKIE, load_course, render_learn, toggle_item, token_ok

    headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}

    if request.method == "POST":
        form = await request.form()
        action = str(form.get("action") or "")
        if action == "logout":
            resp = HTMLResponse(render_learn(authed=False), headers=headers)
            resp.delete_cookie(COOKIE, path="/")
            return resp
        if action == "toggle":
            token = (request.cookies.get(COOKIE) or "").strip()
            if not token_ok(token):
                return HTMLResponse(
                    render_learn(authed=False, err="Войдите снова"),
                    headers=headers,
                )
            try:
                cid = int(form.get("checklist_id") or 0)
                iid = int(form.get("item_id") or 0)
            except ValueError:
                cid = iid = 0
            status = str(form.get("status") or "done")
            if status not in ("done", "todo"):
                status = "done"
            terr = toggle_item(token, cid, iid, status) if cid and iid else "bad-id"
            open_id = None
            try:
                open_id = int(form.get("open") or cid or 0) or None
            except ValueError:
                open_id = cid or None
            course = load_course(token)
            if terr:
                # всё равно показать курс
                pass
            return HTMLResponse(
                render_learn(
                    course=course, authed=True, token=token, open_id=open_id
                ),
                headers=headers,
            )
        token = str(form.get("token") or "").strip()
        if not token_ok(token):
            return HTMLResponse(
                render_learn(authed=False, err="Неверный токен"),
                headers=headers,
            )
        fwd = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
        resp = RedirectResponse("/go-learn/", status_code=303)
        resp.set_cookie(
            COOKIE,
            token,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            samesite="lax",
            secure=fwd == "https",
            path="/",
        )
        for k, v in headers.items():
            resp.headers[k] = v
        return resp

    token = (request.cookies.get(COOKIE) or "").strip()
    if not token_ok(token):
        return HTMLResponse(render_learn(authed=False), headers=headers)
    open_id = None
    try:
        q = request.query_params.get("open")
        open_id = int(q) if q else None
    except ValueError:
        open_id = None
    course = load_course(token)
    return HTMLResponse(
        render_learn(course=course, authed=True, token=token, open_id=open_id),
        headers=headers,
    )


@app.get("/go-tasks/full")
@app.get("/go-tasks/full/")
async def go_tasks_full_handoff():
    """Полный UI на ПК не стартует. Ведём на список, который открывается."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse("/go-tasks/", status_code=302)


@app.api_route("/go-tasks", methods=["GET", "POST"])
@app.api_route("/go-tasks/", methods=["GET", "POST"])
async def go_tasks_emergency(request: Request):
    """Вход для ПК: токен → cookie; список — запасной; полный UI — /go-tasks/full."""
    import secrets

    from fastapi.responses import HTMLResponse, RedirectResponse

    cookie_name = "empire_go_tasks_token"
    expected = (os.getenv("PLANNING_API_TOKEN") or "").strip()

    def _ok_token(t: str) -> bool:
        t = (t or "").strip()
        return bool(expected) and bool(t) and secrets.compare_digest(t, expected)

    # Без Clear-Site-Data: на части браузеров сносит cookie/storage и ломает вход.
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }

    if request.method == "POST":
        form = await request.form()
        if (form.get("action") or "") == "logout":
            resp = HTMLResponse(_go_tasks_html(authed=False), headers=headers)
            resp.delete_cookie(cookie_name, path="/")
            return resp
        token = str(form.get("token") or "").strip()
        if not _ok_token(token):
            return HTMLResponse(
                _go_tasks_html(authed=False, err="Неверный токен"),
                headers=headers,
            )
        # Сначала SSR-список (всегда открывается на ПК). SPA /x/ — кнопкой с native_token.
        fwd = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
        secure_cookie = fwd == "https"
        # Не шлём Clear-Site-Data на логине — иначе браузер может снести storage до handoff.
        login_headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
        resp = RedirectResponse("/go-tasks/", status_code=303)
        resp.set_cookie(
            cookie_name,
            token,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            samesite="lax",
            secure=secure_cookie,
            path="/",
        )
        for k, v in login_headers.items():
            resp.headers[k] = v
        return resp

    # GET: cookie → мост со списком + кнопка полного UI
    token = (request.cookies.get(cookie_name) or "").strip()
    if _ok_token(token):
        tasks, ferr = _go_tasks_fetch(token)
        if tasks is not None and not ferr:
            return HTMLResponse(
                _go_tasks_html(tasks=tasks, authed=True, token=token),
                headers=headers,
            )
        if ferr == "auth":
            resp = HTMLResponse(
                _go_tasks_html(authed=False, err="Токен устарел — введите снова"),
                headers=headers,
            )
            resp.delete_cookie(cookie_name, path="/")
            return resp
        return HTMLResponse(
            _go_tasks_html(authed=False, err=f"Ошибка: {ferr or 'unknown'}"),
            headers=headers,
        )

    return HTMLResponse(_go_tasks_html(authed=False), headers=headers)


@app.get("/")
async def home(request: Request):
    if _is_snegiri_host(request):
        return _snegiri_file("index.html")
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


@app.get("/gift")
async def gift_page(request: Request):
    return templates.TemplateResponse(
        request,
        "gift.html",
        _ctx(
            request,
            metrika_page="gift",
            gift_pdf_url=GIFT_PDF_URL,
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
async def robots(request: Request):
    if _is_snegiri_host(request):
        return (
            "User-agent: *\nAllow: /\n"
            f"Sitemap: https://{SNEGIRI_CANONICAL}/sitemap.xml\n"
        )
    return (
        f"User-agent: *\nAllow: /\nAllow: /rss/\nDisallow: /admin/\nDisallow: /portfolio\nDisallow: /hub\n"
        f"Sitemap: https://{CANONICAL_HOST}/sitemap.xml\n"
    )


@app.get("/sitemap.xml")
async def sitemap(request: Request):
    if _is_snegiri_host(request):
        urls = [
            f"https://{SNEGIRI_CANONICAL}/",
            f"https://{SNEGIRI_CANONICAL}/app.html",
            f"https://{SNEGIRI_CANONICAL}/comics.html",
        ]
        body = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        body.extend(f"  <url><loc>{u}</loc></url>" for u in urls)
        body.append("</urlset>")
        return Response(content="\n".join(body), media_type="application/xml")
    book = _load_json(BASE_DIR / "data" / "book" / "napensiyu_nikogda.json")
    articles = await _fetch_published_articles(limit=200)

    urls: list[str] = [
        f"https://{CANONICAL_HOST}/",
        f"https://{CANONICAL_HOST}/book",
        f"https://{CANONICAL_HOST}/buy",
        f"https://{CANONICAL_HOST}/gift",
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


@app.get("/{full_path:path}")
async def snegiri_static(request: Request, full_path: str):
    """Лендинг/PWA «Снегири не гири» по Host snegirinegiri.ru."""
    if not _is_snegiri_host(request):
        raise HTTPException(status_code=404)
    rel = (full_path or "").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise HTTPException(status_code=404)
    target = SNEGIRI_ROOT / rel
    if target.is_dir():
        rel = f"{rel.rstrip('/')}/index.html"
    return _snegiri_file(rel)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
