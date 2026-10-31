"""HTML-кабинет портфеля в стиле Snowball (без Streamlit)."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from portfolio.asset_classify import ASSET_CLASS_LABELS
from portfolio.auth import (
    COOKIE_NAME,
    COOKIE_PATH,
    cookie_ok,
    expected_password,
    password_matches,
    session_token,
)
from portfolio.calc.metrics import compute_metrics, fmt_pct, fmt_rub, fmt_xirr
from portfolio.config import DEFAULT_CUSHION_RUB
from portfolio.db import db_session, get_setting, init_db
from portfolio import db as pdb

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

_PALETTE = ["#0d9488", "#2563eb", "#f59e0b", "#8b5cf6", "#64748b", "#ef4444"]


def _donut(items: list[dict], value_key: str = "value") -> str:
    total = sum(float(i.get(value_key) or 0) for i in items) or 1.0
    parts: list[str] = []
    acc = 0.0
    for i, item in enumerate(items):
        color = _PALETTE[i % len(_PALETTE)]
        item["color"] = color
        pct = float(item.get(value_key) or 0) / total * 100
        start = acc
        acc += pct
        parts.append(f"{color} {start:.3f}% {acc:.3f}%")
    if not parts:
        return "conic-gradient(#334155 0 100%)"
    return f"conic-gradient({', '.join(parts)})"


def _chart(daily: list[dict]) -> dict | None:
    if len(daily) < 2:
        return None
    vals = [float(p["value"]) for p in daily]
    vmin, vmax = min(vals), max(vals)
    span = (vmax - vmin) or 1.0
    w, h, pad = 720, 220, 12
    coords: list[str] = []
    n = len(vals)
    for i, v in enumerate(vals):
        x = pad + (i / (n - 1)) * (w - 2 * pad)
        y = (h - pad) - ((v - vmin) / span) * (h - 2 * pad)
        coords.append(f"{x:.1f},{y:.1f}")
    area = f"{pad},{h - pad} " + " ".join(coords) + f" {w - pad},{h - pad}"
    return {
        "w": w,
        "h": h,
        "line": " ".join(coords),
        "area": area,
        "first": daily[0]["date"],
        "last": daily[-1]["date"],
        "min": vmin,
        "max": vmax,
    }


_bundle_cache = None
_bundle_at = 0.0
_bundle_stamp = None
_BUNDLE_TTL = 20.0


def _db_stamp():
    p = pdb.PORTFOLIO_DB
    try:
        st = p.stat()
        return (str(p), st.st_mtime_ns, st.st_size)
    except OSError:
        return (str(p), 0, 0)


def _load():
    global _bundle_cache, _bundle_at, _bundle_stamp
    now = time.monotonic()
    stamp = _db_stamp()
    if (
        _bundle_cache is not None
        and now - _bundle_at < _BUNDLE_TTL
        and _bundle_stamp == stamp
    ):
        return _bundle_cache
    with db_session(timeout=3, busy_ms=2000) as conn:
        init_db(conn)
        m, rows = compute_metrics(conn, live_prices=False)
        cushion = float(get_setting(conn, "cushion_rub", str(DEFAULT_CUSHION_RUB)))
        daily_rows = conn.execute(
            "SELECT snap_date, total_value FROM daily_snapshots ORDER BY snap_date"
        ).fetchall()
        daily = [{"date": r["snap_date"], "value": float(r["total_value"])} for r in daily_rows]
    for r in rows:
        r["class_label"] = ASSET_CLASS_LABELS.get(r.get("asset_class"), r.get("asset_class") or "—")
    liq_total = sum(r["market_value"] or 0 for r in rows if r.get("asset_class") == "liquidity")
    _bundle_cache = m, rows, cushion, liq_total, daily
    _bundle_at = now
    _bundle_stamp = stamp
    return _bundle_cache


def invalidate_bundle() -> None:
    global _bundle_cache, _bundle_at, _bundle_stamp
    _bundle_cache = None
    _bundle_at = 0.0
    _bundle_stamp = None


def _ctx(authed: bool, *, error: str | None = None, bundle=None) -> dict:
    ctx: dict = {
        "authed": authed,
        "error": error,
        "m": None,
        "rows": [],
        "fmt_rub": fmt_rub,
        "fmt_pct": fmt_pct,
        "fmt_xirr": fmt_xirr,
        "cushion": 0.0,
        "liq_total": 0.0,
        "excess": 0.0,
        "shortfall": 0.0,
        "class_donut": "",
        "broker_donut": "",
        "chart": None,
        "brokers": [],
        "classes": [],
        "total_income": 0.0,
        "div_yield": None,
        "refresh_action": "/portfolio/refresh",
        "logout_href": "/portfolio/logout",
    }
    if not authed or not bundle:
        return ctx
    m, rows, cushion, liq_total, daily = bundle
    by_class = [dict(x) for x in m.by_class]
    by_broker = [dict(x) for x in m.by_broker]
    m.by_class = by_class
    m.by_broker = by_broker
    ctx.update(
        {
            "m": m,
            "rows": rows,
            "cushion": cushion,
            "liq_total": liq_total,
            "excess": max(0.0, liq_total - cushion),
            "shortfall": max(0.0, cushion - liq_total),
            "class_donut": _donut(by_class),
            "broker_donut": _donut(by_broker),
            "chart": _chart(daily),
            "brokers": [b["broker"] for b in by_broker],
            "classes": [c["label"] for c in by_class],
            "total_income": (m.profit_abs or 0) + m.dividends + m.coupons,
            "div_yield": (m.dividends / m.total_value * 100) if m.total_value > 0 and m.dividends else None,
        }
    )
    return ctx


def _secure(request: Request) -> bool:
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").split(",")[0].strip()
    return proto == "https"


@router.get("/portfolio", response_class=HTMLResponse)
async def portfolio_get(request: Request, empire_pf: str | None = Cookie(default=None)):
    if not cookie_ok(empire_pf):
        return templates.TemplateResponse(request, "portfolio.html", _ctx(False))
    return templates.TemplateResponse(request, "portfolio.html", _ctx(True, bundle=_load()))


@router.post("/portfolio/login")
async def portfolio_login(request: Request, password: str = Form(default="")):
    expected = expected_password()
    if not expected or not password_matches(password, expected):
        return templates.TemplateResponse(
            request, "portfolio.html", _ctx(False, error="Неверный пароль"), status_code=401
        )
    resp = RedirectResponse("/portfolio", status_code=303)
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
    return resp


@router.get("/portfolio/logout")
async def portfolio_logout():
    resp = RedirectResponse("/portfolio", status_code=303)
    resp.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)
    resp.delete_cookie(COOKIE_NAME, path="/portfolio")
    return resp


@router.post("/portfolio/refresh")
async def portfolio_refresh(empire_pf: str | None = Cookie(default=None)):
    if not cookie_ok(empire_pf):
        return RedirectResponse("/portfolio", status_code=303)
    from portfolio.sync import refresh_prices_background

    refresh_prices_background(force=True)
    return RedirectResponse("/portfolio?ok=prices", status_code=303)
