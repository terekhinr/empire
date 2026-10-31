"""Маршруты HTML-кабинета «Око Саурона»."""

from __future__ import annotations

import asyncio
import os
import sqlite3
import time
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from dashboard_ops import OPTIONAL_BOTS, service_row
from empire_flags import load_empire_flags, save_empire_flags
from portfolio.auth import (
    COOKIE_NAME,
    COOKIE_PATH,
    cookie_ok,
    expected_password,
    password_matches,
    session_token,
)
from portfolio.web_routes import _ctx as portfolio_ctx
from portfolio.web_routes import _load as portfolio_load
from sauron.nav import DEFAULT_PAGE, SECTIONS, TITLES, section_for

router = APIRouter()
_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
_EMPIRE_DB = Path(__file__).resolve().parent.parent / "empire.db"

CORE_UNITS = [
    "empire_main",
    "empire_worker",
    "empire_webapp",
    "empire_dashboard",
    "empire_gdepar",
    "empire_sales",
    "empire_ha_notify",
]

PUBLISH_CHANNELS = [
    ("tg", "Telegram"),
    ("dzen_rss", "Дзен RSS"),
    ("vk_wall", "VK стена"),
    ("vc_ru", "VC.ru (заглушка)"),
    ("max", "MAX (заглушка)"),
]

FLAG_LABELS = {
    "stop_publications": "Стоп публикаций",
    "stop_worker": "Стоп worker",
    "stop_scout": "Стоп scout",
    "stop_neurocomment": "Стоп нейрокомментинга",
    "stop_sales": "Стоп продаж",
    "stop_spy": "Стоп разведки",
}

_STUB_EXTRA = {
    "core": [],
    "bots": [],
    "disk": None,
    "counts": {
        "tasks_todo": 0,
        "tasks_doing": 0,
        "tasks_done": 0,
        "goals_active": 0,
        "projects_active": 0,
    },
    "flags": {},
    "flag_items": [(k, FLAG_LABELS[k], False) for k in FLAG_LABELS],
    "ytd": {
        "expense_ytd_rub": 0,
        "income_sales_ytd_rub": 0,
        "margin_ytd_rub": 0,
        "expense_cursor_ytd_rub": 0,
        "expense_openrouter_ytd_rub": 0,
        "expense_fal_ytd_rub": 0,
        "expense_ai_tools_ytd_rub": 0,
    },
    "alert": {"pct": 0, "alert": False, "revenue_ytd_rub": 0},
    "month_key": "",
    "month_cats": [],
    "pl_rows": [],
    "stop_sales": False,
    "products": [],
    "summary": None,
    "recent": [],
    "tasks": [],
    "drafts": [],
    "channels": PUBLISH_CHANNELS,
    "items": [],
    "now": "",
    "queue": [],
    "due": [],
    "incoming": "",
    "news": [],
    "waitlist": 0,
    "metrika_id": "",
    "subs": {},
    "weekly": [],
    "yt": "",
    "dzen": "",
    "vk": "",
    "links": [],
    "live": False,
    "configured": False,
    "session_ready": False,
    "stop_spy": False,
    "scripts": [],
    "plans": [],
    "pubs": [],
    "last_file": None,
    "last_json": None,
    "insights": {"hypotheses": []},
}


def _secure(request: Request) -> bool:
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").split(",")[0].strip()
    return proto == "https"


def _bust_stale_client(resp: Response) -> None:
    """Снести кэш и service worker Streamlit, из‑за них Chrome рвёт вкладки."""
    resp.headers["Clear-Site-Data"] = '"cache", "storage"'


def _set_login_cookie(resp: RedirectResponse, request: Request) -> None:
    resp.set_cookie(
        COOKIE_NAME,
        session_token(),
        httponly=True,
        secure=_secure(request),
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path=COOKIE_PATH,
    )
    resp.delete_cookie(COOKIE_NAME, path="/portfolio")
    _bust_stale_client(resp)


def _clear_login_cookie(resp: RedirectResponse) -> None:
    resp.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)
    resp.delete_cookie(COOKIE_NAME, path="/portfolio")


def _empire() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_EMPIRE_DB), timeout=3)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=3000")
    except sqlite3.Error:
        pass
    return conn


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    try:
        conn = _empire()
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    except sqlite3.Error:
        return []


def _login_ctx(request: Request, error: str | None = None) -> dict:
    return {"request": request, "error": error}


def _page_ctx(request: Request, page: str, extra: dict | None = None, flash: str | None = None) -> dict:
    ctx = {
        "request": request,
        "page": page,
        "title": TITLES.get(page, "Око Саурона"),
        "sections": SECTIONS,
        "section": section_for(page),
        "flash": flash or request.query_params.get("ok"),
        "err": request.query_params.get("err"),
    }
    if extra:
        ctx.update({k: v for k, v in extra.items() if k != "bundle"})
    if page == "portfolio":
        try:
            bundle = extra.get("bundle") if extra else None
            if bundle is not None:
                ctx.update(portfolio_ctx(True, bundle=bundle))
                all_rows = list(ctx.get("rows") or [])
                ctx["rows_total"] = len(all_rows)
        except Exception:
            ctx["err"] = ctx.get("err") or "portfolio_load"
        ctx["page"] = "portfolio"
        ctx["refresh_action"] = "/hub/portfolio/refresh"
        ctx["logout_href"] = "/hub/logout"
    return ctx


def _guard(empire_pf: str | None):
    if cookie_ok(empire_pf):
        return None
    return RedirectResponse("/hub/login", status_code=303)


@router.get("/hub", response_class=HTMLResponse)
@router.get("/hub/", response_class=HTMLResponse)
async def hub_root(empire_pf: str | None = Cookie(default=None)):
    if not cookie_ok(empire_pf):
        return RedirectResponse("/hub/login", status_code=303)
    return RedirectResponse(f"/hub/{DEFAULT_PAGE}", status_code=303)


_KILL_SW = """
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil((async function () {
    try {
      var keys = await caches.keys();
      await Promise.all(keys.map(function (k) { return caches.delete(k); }));
    } catch (err) {}
    await self.registration.unregister();
  })());
});
""".strip()


@router.get("/hub/sw.js")
async def hub_kill_sw():
    return Response(
        _KILL_SW,
        media_type="application/javascript",
        headers={"Cache-Control": "no-store", "Service-Worker-Allowed": "/hub/"},
    )


@router.api_route("/hub/_stcore/{rest:path}", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def hub_no_streamlit(rest: str):
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/hub/login", response_class=HTMLResponse)
async def hub_login_get(request: Request, empire_pf: str | None = Cookie(default=None)):
    if cookie_ok(empire_pf):
        return RedirectResponse(f"/hub/{DEFAULT_PAGE}", status_code=303)
    resp = _TEMPLATES.TemplateResponse(request, "sauron_login.html", _login_ctx(request))
    _bust_stale_client(resp)
    return resp


@router.post("/hub/login")
async def hub_login_post(request: Request, password: str = Form(default="")):
    expected = expected_password()
    if not expected or not password_matches(password, expected):
        return _TEMPLATES.TemplateResponse(
            request, "sauron_login.html", _login_ctx(request, "Неверный пароль"), status_code=401
        )
    resp = RedirectResponse(f"/hub/{DEFAULT_PAGE}", status_code=303)
    _set_login_cookie(resp, request)
    return resp


@router.get("/hub/logout")
async def hub_logout():
    resp = RedirectResponse("/hub/login", status_code=303)
    _clear_login_cookie(resp)
    return resp


_counts_cache: tuple[float, dict] | None = None


def _monitoring_data() -> dict:
    global _counts_cache
    core = [service_row(u) for u in CORE_UNITS]
    bots = []
    for unit, meta in OPTIONAL_BOTS.items():
        row = service_row(unit)
        row["label"] = meta["label"]
        row["note"] = meta["note"]
        bots.append(row)
    disk = None
    try:
        stv = os.statvfs("/")
        disk = {
            "free": (stv.f_bavail * stv.f_frsize) / (1024**3),
            "total": (stv.f_blocks * stv.f_frsize) / (1024**3),
        }
    except OSError:
        pass
    counts = {}
    now = time.monotonic()
    if _counts_cache and now - _counts_cache[0] < 30:
        counts = _counts_cache[1]
    else:
        conn = _empire()
        try:
            for tbl in ("news", "spy_signals", "jobs", "publications", "post_drafts"):
                try:
                    counts[tbl] = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                except sqlite3.Error:
                    counts[tbl] = None
        finally:
            conn.close()
        _counts_cache = (now, counts)
    return {"core": core, "bots": bots, "disk": disk, "counts": counts}


def _finance_data() -> dict:
    from finance_ledger import (
        EXPENSE_CATEGORY_LABELS,
        build_pl_monthly,
        expense_by_category,
        ytd_totals,
    )
    from sales_db import init_sales_db, npd_limit_alert

    init_sales_db()
    ytd = ytd_totals()
    alert = npd_limit_alert()
    month_key = date.today().strftime("%Y-%m")
    month_cats = [
        {"label": EXPENSE_CATEGORY_LABELS.get(k, k), "code": k, "amount": v}
        for k, v in sorted(expense_by_category(month=month_key).items(), key=lambda x: -x[1])
        if v > 0
    ]
    return {
        "ytd": ytd,
        "alert": alert,
        "month_key": month_key,
        "month_cats": month_cats,
        "pl_rows": build_pl_monthly(18),
        "stop_sales": load_empire_flags().get("stop_sales"),
    }


def _plain(v):
    if v is None:
        return ""
    try:
        import math
        if isinstance(v, float) and math.isnan(v):
            return ""
    except Exception:
        pass
    s = str(v).strip()
    if s.lower() in ("nan", "nat", "none", "natype"):
        return ""
    return v


def _health_data() -> dict:
    from health_db import latest_measurement_summary, load_measurements_df

    summary = latest_measurement_summary()
    recent = []
    try:
        df = load_measurements_df()
        if not df.empty:
            recs = df.tail(12).iloc[::-1].to_dict("records")
            for rec in recs:
                day = rec.get("measured_on") or rec.get("date") or rec.get("measured_at") or ""
                rec["date"] = str(day)[:10]
                rec["weight_kg"] = rec.get("weight_kg")
                rec["waist_cm"] = rec.get("waist_cm")
            recent = recs
    except Exception:
        pass
    return {"summary": summary, "recent": recent}


def _planning_data() -> dict:
    from planning_db import load_tasks_df, summary_counts

    counts = summary_counts()
    tasks = []
    try:
        df = load_tasks_df()
        open_df = df[df["status"].isin(["todo", "doing"])] if not df.empty else df
        raw = open_df.head(40).to_dict("records") if not open_df.empty else []
        for t in raw:
            t["status"] = _plain(t.get("status"))
            t["title"] = _plain(t.get("title") or t.get("name"))
            t["project"] = _plain(t.get("project_title") or t.get("project"))
        tasks = raw
    except Exception:
        pass
    return {"counts": counts, "tasks": tasks}


def _obsidian_data() -> dict:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import obsidian_content as oc

    now = datetime.now(ZoneInfo("Europe/Moscow"))
    queue = oc.load_queue()
    due = oc.entries_due(now)
    incoming = os.environ.get("OBSIDIAN_EMPIRE_INCOMING", "").strip() or str(
        oc.ROOT / "data" / "obsidian_incoming"
    )
    return {
        "now": now.strftime("%d.%m.%Y %H:%M"),
        "queue": queue[:80],
        "due": due,
        "incoming": incoming,
    }


def _longread_data() -> dict:
    import longread_empire as le

    items = []
    for num, title in le.META:
        items.append(
            {
                "num": num,
                "title": title,
                "dzen": le.longread_md_path(num, "dzen").is_file(),
                "vk": le.longread_md_path(num, "vk").is_file(),
            }
        )
    return {"items": items}


def _pension_summary_data() -> dict:
    from pension_metrics import latest_daily_subs, load_weekly_metrics, waitlist_count

    mid = (os.getenv("YANDEX_METRIKA_ID") or "").strip()
    subs = latest_daily_subs()
    weekly = []
    try:
        weekly = load_weekly_metrics()[-12:]
    except Exception:
        pass
    return {
        "waitlist": waitlist_count(),
        "metrika_id": mid if mid.isdigit() else "",
        "subs": subs,
        "weekly": weekly,
        "yt": os.getenv("PENSION_YOUTUBE_URL") or "",
        "dzen": os.getenv("PENSION_DZEN_URL") or "",
        "vk": os.getenv("PENSION_VK_URL") or "",
    }


def _ai_data() -> dict:
    import json
    from pathlib import Path as P

    from metrics import build_ai_insights_stub, weekly_events_summary

    files = sorted(P("data/insights").glob("insights_*.json"), reverse=True) if P("data/insights").is_dir() else []
    last_json = None
    if files:
        try:
            last_json = json.loads(files[0].read_text(encoding="utf-8"))
        except Exception:
            last_json = {"file": files[0].name, "error": "не прочитан"}
    return {
        "last_file": files[0].name if files else None,
        "last_json": last_json,
        "summary": weekly_events_summary() or {"note": "пусто"},
        "insights": build_ai_insights_stub(),
    }


def _extra_for(page: str) -> dict:
    if page == "portfolio":
        return {"bundle": portfolio_load()}
    if page == "monitoring":
        return _monitoring_data()
    if page == "flags":
        flags = load_empire_flags()
        return {"flags": flags, "flag_items": [(k, FLAG_LABELS.get(k, k), flags.get(k)) for k in FLAG_LABELS]}
    if page == "finance":
        return _finance_data()
    if page == "sales":
        from sales_db import init_sales_db, list_products, npd_limit_alert

        init_sales_db()
        prods = []
        try:
            prods = list_products()
        except Exception:
            pass
        return {"alert": npd_limit_alert(), "products": prods, "stop_sales": load_empire_flags().get("stop_sales")}
    if page == "health":
        return _health_data()
    if page == "planning":
        return _planning_data()
    if page == "moderation":
        drafts = _rows("SELECT * FROM post_drafts WHERE status='pending' ORDER BY created_at DESC LIMIT 25")
        return {"drafts": drafts, "channels": PUBLISH_CHANNELS}
    if page == "obsidian":
        return _obsidian_data()
    if page == "longread":
        return _longread_data()
    if page == "pension-news":
        news = _rows(
            "SELECT id, title, category, source, published_at, url FROM news ORDER BY id DESC LIMIT 40"
        )
        if not news:
            news = _rows("SELECT * FROM news ORDER BY rowid DESC LIMIT 40")
        return {"news": news}
    if page == "pension-summary":
        return _pension_summary_data()
    if page == "sources":
        from empire_sources import list_links

        return {"links": list_links(50)}
    if page == "spy":
        from spy_config import spy_live_enabled, telethon_configured, telethon_session_ready

        return {
            "live": spy_live_enabled(),
            "configured": telethon_configured(),
            "session_ready": telethon_session_ready(),
            "stop_spy": load_empire_flags().get("stop_spy"),
        }
    if page == "shorts":
        return {"scripts": _rows(
            "SELECT id, persona_key, title, hook, duration_sec, status, trend_ref, created_at "
            "FROM shorts_scripts ORDER BY created_at DESC LIMIT 40"
        )}
    if page == "neurocomment":
        return {"plans": _rows(
            "SELECT id, persona_key, channel_ref, substr(planned_text,1,80) AS text, "
            "reason, status, created_at FROM neurocomment_plans ORDER BY created_at DESC LIMIT 30"
        )}
    if page == "analytics":
        drafts = _rows(
            "SELECT persona_key, status, count(*) as cnt FROM post_drafts GROUP BY persona_key, status"
        )
        pubs = _rows(
            "SELECT persona_key, count(*) as cnt FROM publications GROUP BY persona_key"
        )
        return {"drafts": drafts, "pubs": pubs}
    if page == "ai":
        return _ai_data()
    return {}


@router.get("/hub/{page}", response_class=HTMLResponse)
async def hub_page(request: Request, page: str, empire_pf: str | None = Cookie(default=None)):
    bounced = _guard(empire_pf)
    if bounced:
        return bounced
    if page not in TITLES:
        return RedirectResponse(f"/hub/{DEFAULT_PAGE}", status_code=303)
    extra = {}
    extra_err = None
    try:
        extra = await asyncio.wait_for(asyncio.to_thread(_extra_for, page), timeout=8)
    except asyncio.TimeoutError:
        extra_err = f"{page}: timeout"
        extra = dict(_STUB_EXTRA)
    except Exception as exc:
        extra_err = f"{page}: {type(exc).__name__}"
        extra = dict(_STUB_EXTRA)
    try:
        ctx = _page_ctx(request, page, extra)
        if extra_err:
            ctx["err"] = extra_err
        return _TEMPLATES.TemplateResponse(request, "sauron.html", ctx)
    except Exception as extra_exc:
        return HTMLResponse(
            f"<!doctype html><title>Око Саурона</title><p>Страница «{page}» не собралась ({type(extra_exc).__name__}). Обновите.</p>",
            status_code=500,
        )


@router.post("/hub/flags")
async def hub_flags_save(
    request: Request,
    empire_pf: str | None = Cookie(default=None),
    stop_publications: str | None = Form(default=None),
    stop_worker: str | None = Form(default=None),
    stop_scout: str | None = Form(default=None),
    stop_neurocomment: str | None = Form(default=None),
    stop_sales: str | None = Form(default=None),
    stop_spy: str | None = Form(default=None),
):
    bounced = _guard(empire_pf)
    if bounced:
        return bounced
    save_empire_flags(
        {
            "stop_publications": bool(stop_publications),
            "stop_worker": bool(stop_worker),
            "stop_scout": bool(stop_scout),
            "stop_neurocomment": bool(stop_neurocomment),
            "stop_sales": bool(stop_sales),
            "stop_spy": bool(stop_spy),
        }
    )
    return RedirectResponse("/hub/flags?ok=saved", status_code=303)


@router.post("/hub/moderation/{draft_id}/save")
async def hub_mod_save(
    draft_id: int,
    empire_pf: str | None = Cookie(default=None),
    text_content: str = Form(default=""),
):
    bounced = _guard(empire_pf)
    if bounced:
        return bounced
    conn = _empire()
    try:
        conn.execute("UPDATE post_drafts SET text_content=? WHERE id=?", (text_content, draft_id))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/hub/moderation?ok=saved", status_code=303)


@router.post("/hub/moderation/{draft_id}/delete")
async def hub_mod_delete(draft_id: int, empire_pf: str | None = Cookie(default=None)):
    bounced = _guard(empire_pf)
    if bounced:
        return bounced
    conn = _empire()
    try:
        conn.execute("DELETE FROM post_drafts WHERE id=?", (draft_id,))
        conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/hub/moderation?ok=deleted", status_code=303)


@router.post("/hub/moderation/{draft_id}/publish")
async def hub_mod_publish(
    request: Request,
    draft_id: int,
    empire_pf: str | None = Cookie(default=None),
    text_content: str = Form(default=""),
):
    bounced = _guard(empire_pf)
    if bounced:
        return bounced
    form = await request.form()
    picked = [str(v) for v in form.getlist("channels") if v]
    conn = _empire()
    try:
        row = conn.execute("SELECT * FROM post_drafts WHERE id=?", (draft_id,)).fetchone()
        if not row:
            return RedirectResponse("/hub/moderation?err=notfound", status_code=303)
        row = dict(row)
        conn.execute("UPDATE post_drafts SET text_content=? WHERE id=?", (text_content, draft_id))
        conn.commit()
        picked = [c for c in picked if c]
        if not picked:
            return RedirectResponse("/hub/moderation?err=channels", status_code=303)
        os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")
        from empire_publish import publish_draft_multi
        from main import async_session, init_db

        await init_db()
        async with async_session() as session:
            results = await publish_draft_multi(
                session,
                content_id=draft_id,
                channels=picked,
                text=text_content,
                image_path=row.get("image_path"),
                persona_key=row["persona_key"],
            )
        ok_any = any(getattr(r, "ok", False) for r in results)
        if ok_any or row["persona_key"] == "pension":
            conn.execute("UPDATE post_drafts SET status='published' WHERE id=?", (draft_id,))
            conn.commit()
    finally:
        conn.close()
    return RedirectResponse("/hub/moderation?ok=published", status_code=303)


@router.post("/hub/obsidian/import")
async def hub_obsidian_import(empire_pf: str | None = Cookie(default=None)):
    bounced = _guard(empire_pf)
    if bounced:
        return bounced
    import obsidian_content as oc

    oc.run_import_if_needed(force=True)
    return RedirectResponse("/hub/obsidian?ok=imported", status_code=303)


@router.post("/hub/sources")
async def hub_sources_create(
    empire_pf: str | None = Cookie(default=None),
    persona: str = Form(default="pension"),
    label: str = Form(default=""),
):
    bounced = _guard(empire_pf)
    if bounced:
        return bounced
    from empire_sources import generate_source_id, register_link

    sid = generate_source_id(persona, label)
    register_link(sid, persona, label)
    return RedirectResponse("/hub/sources?ok=" + sid, status_code=303)


@router.post("/hub/portfolio/refresh")
async def hub_portfolio_refresh(empire_pf: str | None = Cookie(default=None)):
    bounced = _guard(empire_pf)
    if bounced:
        return bounced
    from portfolio.sync import refresh_prices_background

    refresh_prices_background(force=True)
    return RedirectResponse("/hub/portfolio?ok=prices", status_code=303)
