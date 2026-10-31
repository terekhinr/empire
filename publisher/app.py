"""Веб-оболочка Ops Studio: база, ИИ-фабрика, матрица, автопост-бот, алерты."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Cookie, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from publisher.bank import (
    bank_days_remaining,
    fill_slots_from_bank,
    import_gemini_pack_to_bank,
    new_bank_post,
)
from publisher.catalog import PROJECTS, WEEKDAYS_RU, project_by_id
from publisher.dispatch import live_allowed, tick
from publisher.media import list_archive_images
from publisher.notify import (
    normalize_bot_settings,
    resolve_admin_chat_id,
    send_admin_text,
    telegram_token,
)
from publisher.parse import parse_matrix_text, parse_post_file
from publisher.rubrics import IMAGE_MODES, find_rubric, normalize_rubric_id, rubric_public
from publisher.schedule import assign_next_slots, format_hhmm, week_grid
from publisher.store import Store, new_id, utc_now_iso

MSK = ZoneInfo("Europe/Moscow")
BASE_DIR = Path(__file__).resolve().parent.parent
COOKIE_NAME = "empire_studio"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30

router = APIRouter(prefix="/admin/studio", tags=["publisher-studio"])

_templates: Jinja2Templates | None = None
_store: Store | None = None


def configure(templates: Jinja2Templates, store: Store | None = None) -> None:
    global _templates, _store
    _templates = templates
    _store = store or Store()


def get_store() -> Store:
    return _store or Store()


def _studio_token() -> str:
    return (
        os.getenv("EMPIRE_STUDIO_TOKEN", "").strip()
        or os.getenv("BANYA_ADMIN_TOKEN", "").strip()
    )


def _open_unauth() -> bool:
    return os.getenv("EMPIRE_STUDIO_OPEN", "").strip() in ("1", "true", "yes")


def _is_authed(cookie: str | None) -> bool:
    token = _studio_token()
    if _open_unauth() and not token:
        return True
    if not token:
        return False
    return bool(cookie) and cookie == token


def _require(cookie: str | None) -> None:
    token = _studio_token()
    if not token and not _open_unauth():
        raise HTTPException(
            status_code=503,
            detail="EMPIRE_STUDIO_TOKEN (или BANYA_ADMIN_TOKEN) не задан — оболочка выключена.",
        )
    if not _is_authed(cookie):
        raise HTTPException(status_code=401, detail="unauthorized")


def _tpl() -> Jinja2Templates:
    if _templates is None:
        return Jinja2Templates(directory=str(BASE_DIR / "templates"))
    return _templates


@router.api_route("/login", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def login_page(request: Request, empire_studio: str | None = Cookie(default=None)):
    if _is_authed(empire_studio):
        return RedirectResponse(url="/admin/studio", status_code=303)
    return _tpl().TemplateResponse(
        request,
        "publisher_login.html",
        {"request": request, "error": False},
    )


@router.post("/login")
async def login_submit(request: Request, token: str = Form(...)):
    expected = _studio_token()
    if expected and token.strip() == expected:
        resp = RedirectResponse(url="/admin/studio", status_code=303)
        resp.set_cookie(
            COOKIE_NAME,
            expected,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/admin/studio",
        )
        return resp
    return _tpl().TemplateResponse(
        request,
        "publisher_login.html",
        {"request": request, "error": True},
        status_code=401,
    )


@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/admin/studio/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME, path="/admin/studio")
    return resp


@router.api_route("", methods=["GET", "HEAD"], response_class=HTMLResponse)
@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def studio_home(request: Request, empire_studio: str | None = Cookie(default=None)):
    if not _is_authed(empire_studio):
        if not _studio_token() and not _open_unauth():
            raise HTTPException(
                status_code=503,
                detail="EMPIRE_STUDIO_TOKEN (или BANYA_ADMIN_TOKEN) не задан — оболочка выключена.",
            )
        return RedirectResponse(url="/admin/studio/login", status_code=303)
    return _tpl().TemplateResponse(
        request,
        "publisher_studio.html",
        {
            "request": request,
            "projects": PROJECTS,
            "weekdays": WEEKDAYS_RU,
        },
    )


@router.get("/api/state")
async def api_state(
    week: str | None = None,
    project: str | None = None,
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    data = get_store().load()
    now = datetime.now(MSK)
    if week:
        try:
            ws = datetime.strptime(week, "%Y-%m-%d").replace(tzinfo=MSK)
        except ValueError:
            ws = now
    else:
        ws = now
    pid = (project or "").strip() or None
    grid = week_grid(data["slots"], data["posts"], week_start=ws, project_id=pid)
    counts = _status_counts(data["posts"], pid)
    settings = normalize_bot_settings(data.get("bot_settings"))
    bank = data.get("bank_posts") or []
    if pid:
        bank_view = [b for b in bank if b.get("project_id") == pid]
    else:
        bank_view = bank
    archive_counts = {
        p["persona"]: len(list_archive_images(p["persona"]))
        for p in PROJECTS
        if p.get("kind") == "telegram"
    }
    return JSONResponse(
        {
            "mode": data.get("mode") or "test",
            "live_allowed": live_allowed(),
            "now": now.strftime("%Y-%m-%d %H:%M"),
            "projects": PROJECTS,
            "weekdays": list(WEEKDAYS_RU),
            "grid": grid,
            "slots": [s for s in data["slots"] if not pid or s.get("project_id") == pid],
            "posts": _posts_public(data["posts"], pid),
            "outbox": list(reversed(data.get("outbox") or []))[:40],
            "counts": counts,
            "bank_posts": [_bank_public(b) for b in bank_view][:200],
            "bank_days": bank_days_remaining(data),
            "bank_count": len(bank_view),
            "ai_drafts": list(data.get("ai_drafts") or [])[:50],
            "rubrics": [
                rubric_public(r)
                for r in (data.get("rubrics") or [])
                if not pid or r.get("project_id") == pid
            ],
            "image_modes": list(IMAGE_MODES),
            "bot_settings": settings,
            "bot_env": {
                "has_token": bool(telegram_token()),
                "admin_chat_resolved": resolve_admin_chat_id(settings),
                "archive_images": archive_counts,
                "has_gemini": bool(os.getenv("GEMINI_API_KEY", "").strip()),
            },
        }
    )


@router.post("/api/mode")
async def api_mode(
    mode: str = Form(...),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    wanted = (mode or "").strip().lower()
    if wanted not in ("test", "live"):
        raise HTTPException(400, "mode must be test|live")
    if wanted == "live" and not live_allowed():
        raise HTTPException(
            403,
            "Живой режим выключен. Чтобы включить: EMPIRE_PUBLISHER_LIVE=1 в env.",
        )
    with get_store().mutate() as data:
        data["mode"] = wanted
    return JSONResponse({"ok": True, "mode": wanted})


@router.post("/api/slots")
async def api_add_slot(
    project_id: str = Form(...),
    weekday: int = Form(...),
    time: str = Form(...),
    label: str = Form(""),
    rubric_id: str = Form(""),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    if project_by_id(project_id) is None:
        raise HTTPException(400, "unknown project")
    if not (0 <= weekday <= 6):
        raise HTTPException(400, "weekday 0-6")
    t = format_hhmm(time)
    if not t:
        raise HTTPException(400, "time HH:MM")
    rid = normalize_rubric_id(rubric_id) or normalize_rubric_id(label)
    with get_store().mutate() as data:
        for s in data["slots"]:
            if (
                s.get("project_id") == project_id
                and int(s.get("weekday", -1)) == weekday
                and format_hhmm(s.get("time") or "") == t
            ):
                s["enabled"] = True
                if label.strip():
                    s["label"] = label.strip()
                if rid:
                    s["rubric_id"] = rid
                return JSONResponse({"ok": True, "slot": s, "existed": True})
        slot = {
            "id": new_id("slot"),
            "project_id": project_id,
            "weekday": weekday,
            "time": t,
            "label": label.strip() or (rid or ""),
            "rubric_id": rid,
            "enabled": True,
        }
        data["slots"].append(slot)
    return JSONResponse({"ok": True, "slot": slot, "existed": False})


@router.get("/api/rubrics")
async def api_rubrics(
    project: str | None = None,
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    data = get_store().load()
    pid = (project or "").strip() or None
    rows = [
        rubric_public(r)
        for r in (data.get("rubrics") or [])
        if not pid or r.get("project_id") == pid
    ]
    return JSONResponse({"ok": True, "rubrics": rows, "image_modes": list(IMAGE_MODES)})


@router.post("/api/rubrics/{rubric_id}")
async def api_rubric_update(
    rubric_id: str,
    project_id: str = Form(...),
    label: str = Form(""),
    image_mode: str = Form("generate"),
    on_missing: str = Form("stub"),
    image_provider: str = Form("gemini"),
    archive_dir: str = Form(""),
    fixed_image_path: str = Form(""),
    default_prompt_en: str = Form(""),
    enabled: str = Form("1"),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    if project_by_id(project_id) is None:
        raise HTTPException(400, "unknown project")
    mode = (image_mode or "").strip().lower()
    if mode not in IMAGE_MODES:
        raise HTTPException(400, f"image_mode must be one of {IMAGE_MODES}")
    rid = normalize_rubric_id(rubric_id) or rubric_id
    with get_store().mutate() as data:
        r = find_rubric(data, project_id=project_id, rubric_id=rid)
        if r is None:
            r = {
                "id": rid,
                "project_id": project_id,
                "label": label.strip() or rid,
                "enabled": True,
            }
            data.setdefault("rubrics", []).append(r)
        if label.strip():
            r["label"] = label.strip()
        r["image_mode"] = mode
        r["on_missing"] = (on_missing or "stub").strip().lower() or "stub"
        r["image_provider"] = (image_provider or "gemini").strip() or "gemini"
        r["archive_dir"] = (archive_dir or "").strip() or None
        r["fixed_image_path"] = (fixed_image_path or "").strip() or None
        if default_prompt_en.strip():
            r["default_prompt_en"] = default_prompt_en.strip()
        r["enabled"] = enabled.strip() in ("1", "true", "on", "yes")
        return JSONResponse({"ok": True, "rubric": rubric_public(r)})


@router.post("/api/import/gemini")
async def api_import_gemini(
    project_id: str = Form(...),
    text: str = Form(""),
    file: UploadFile | None = File(default=None),
    empire_studio: str | None = Cookie(default=None),
):
    """Пачка Gemini: --- YAML + тело → банк (с антидублями)."""
    _require(empire_studio)
    if project_by_id(project_id) is None:
        raise HTTPException(400, "unknown project")
    src = (text or "").strip()
    if file and file.filename:
        raw = await file.read()
        try:
            src = raw.decode("utf-8")
        except UnicodeDecodeError:
            src = raw.decode("cp1251", errors="replace")
    if not src or "---" not in src:
        raise HTTPException(400, "Нужен текст/файл с блоками --- YAML ---")
    with get_store().mutate() as data:
        result = import_gemini_pack_to_bank(data, src, project_id=project_id)
    return JSONResponse(
        {
            "ok": True,
            "parsed": result["parsed"],
            "added": result["added"],
            "skipped_dup": result["skipped_dup"],
            "dups": result["dups"][:20],
            "posts": [_bank_public(p) for p in result["posts"][:50]],
        }
    )


@router.post("/api/slots/{slot_id}/toggle")
async def api_toggle_slot(slot_id: str, empire_studio: str | None = Cookie(default=None)):
    _require(empire_studio)
    with get_store().mutate() as data:
        for s in data["slots"]:
            if s.get("id") == slot_id:
                s["enabled"] = not bool(s.get("enabled", True))
                return JSONResponse({"ok": True, "slot": s})
    raise HTTPException(404, "slot not found")


@router.post("/api/slots/{slot_id}/delete")
async def api_delete_slot(slot_id: str, empire_studio: str | None = Cookie(default=None)):
    _require(empire_studio)
    with get_store().mutate() as data:
        before = len(data["slots"])
        data["slots"] = [s for s in data["slots"] if s.get("id") != slot_id]
        if len(data["slots"]) == before:
            raise HTTPException(404, "slot not found")
    return JSONResponse({"ok": True})


@router.post("/api/upload")
async def api_upload(
    project_id: str = Form(...),
    files: list[UploadFile] = File(...),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    if project_by_id(project_id) is None:
        raise HTTPException(400, "unknown project")
    parsed: list[dict[str, Any]] = []
    for uf in files:
        name = uf.filename or "post.md"
        if not name.lower().endswith((".md", ".txt", ".markdown")):
            continue
        raw = await uf.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1251", errors="replace")
        parsed.append(parse_post_file(name, text, default_project=project_id))
    if not parsed:
        raise HTTPException(400, "Нужны файлы .md или .txt")
    created = _commit_entries(parsed, default_project=project_id)
    return JSONResponse({"ok": True, "created": created})


@router.post("/api/paste")
async def api_paste(
    project_id: str = Form(...),
    title: str = Form(""),
    body: str = Form(...),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    if project_by_id(project_id) is None:
        raise HTTPException(400, "unknown project")
    text = (body or "").strip()
    if not text:
        raise HTTPException(400, "empty body")
    heading = (title or "").strip()
    blob = f"# {heading}\n\n{text}" if heading else text
    entry = parse_post_file("paste.md", blob, default_project=project_id)
    created = _commit_entries([entry], default_project=project_id)
    return JSONResponse({"ok": True, "created": created})


@router.post("/api/matrix")
async def api_matrix(
    text: str = Form(""),
    project_id: str = Form(""),
    file: UploadFile | None = File(default=None),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    default = (project_id or "").strip() or None
    if default and project_by_id(default) is None:
        raise HTTPException(400, "unknown project")
    src = (text or "").strip()
    if file and file.filename:
        raw = await file.read()
        try:
            src = raw.decode("utf-8")
        except UnicodeDecodeError:
            src = raw.decode("cp1251", errors="replace")
    if not src:
        raise HTTPException(400, "Пустая матрица")
    entries = parse_matrix_text(src, default_project=default)
    if not entries:
        raise HTTPException(400, "Не удалось разобрать матрицу")
    created = _commit_entries(entries, default_project=default)
    return JSONResponse({"ok": True, "created": created})


@router.post("/api/posts/{post_id}/cancel")
async def api_cancel(post_id: str, empire_studio: str | None = Cookie(default=None)):
    _require(empire_studio)
    with get_store().mutate() as data:
        for p in data["posts"]:
            if p.get("id") == post_id:
                p["status"] = "cancelled"
                return JSONResponse({"ok": True})
    raise HTTPException(404, "post not found")


@router.post("/api/posts/{post_id}/reschedule")
async def api_reschedule(
    post_id: str,
    scheduled_at: str = Form(...),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    stamp = scheduled_at.strip()
    try:
        datetime.strptime(stamp[:16], "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(400, "scheduled_at YYYY-MM-DD HH:MM")
    with get_store().mutate() as data:
        for p in data["posts"]:
            if p.get("id") == post_id:
                p["scheduled_at"] = stamp[:16]
                if p.get("status") in ("cancelled", "failed", "queued", "skipped"):
                    p["status"] = "scheduled"
                return JSONResponse({"ok": True, "post": _post_public(p)})
    raise HTTPException(404, "post not found")


@router.post("/api/tick")
async def api_tick(
    force_id: str = Form(""),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    ids = [force_id] if force_id.strip() else None
    result = tick(get_store(), force_ids=ids)
    return JSONResponse({"ok": True, **result})


@router.post("/api/bank")
async def api_bank_add(
    project_id: str = Form(...),
    title: str = Form(""),
    body: str = Form(...),
    category: str = Form("general"),
    image_path: str = Form(""),
    cooldown_days: int = Form(21),
    rubric_id: str = Form(""),
    image_prompt_en: str = Form(""),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    if project_by_id(project_id) is None:
        raise HTTPException(400, "unknown project")
    if not (body or "").strip():
        raise HTTPException(400, "empty body")
    post = new_bank_post(
        project_id=project_id,
        title=title,
        body=body,
        category=category,
        image_path=(image_path or "").strip() or None,
        cooldown_days=cooldown_days,
        rubric_id=(rubric_id or "").strip() or None,
        image_prompt_en=(image_prompt_en or "").strip() or None,
    )
    with get_store().mutate() as data:
        data.setdefault("bank_posts", []).append(post)
    return JSONResponse({"ok": True, "post": _bank_public(post)})


@router.post("/api/bank/{bank_id}/delete")
async def api_bank_delete(bank_id: str, empire_studio: str | None = Cookie(default=None)):
    _require(empire_studio)
    with get_store().mutate() as data:
        before = len(data.get("bank_posts") or [])
        data["bank_posts"] = [b for b in (data.get("bank_posts") or []) if b.get("id") != bank_id]
        if len(data["bank_posts"]) == before:
            raise HTTPException(404, "not found")
    return JSONResponse({"ok": True})


@router.post("/api/bank/{bank_id}/queue")
async def api_bank_queue(bank_id: str, empire_studio: str | None = Cookie(default=None)):
    """Поставить один пост из банка в ближайший свободный слот."""
    _require(empire_studio)
    now = datetime.now(MSK)
    from publisher.bank import bank_to_queue_post, mark_bank_used
    from publisher.schedule import assign_next_slots

    with get_store().mutate() as data:
        bank = data.get("bank_posts") or []
        bp = next((b for b in bank if b.get("id") == bank_id), None)
        if not bp:
            raise HTTPException(404, "not found")
        placed = assign_next_slots(
            [
                {
                    "title": bp.get("title"),
                    "body": bp.get("body"),
                    "project_id": bp.get("project_id"),
                }
            ],
            data["slots"],
            data["posts"],
            after=now,
            default_project=bp.get("project_id"),
        )
        if not placed or placed[0].get("error"):
            raise HTTPException(400, (placed[0].get("error") if placed else "no_slot"))
        item = placed[0]
        post = bank_to_queue_post(
            bp,
            scheduled_at=item["scheduled_at"],
            slot_id=item.get("slot_id"),
        )
        data["posts"].append(post)
        mark_bank_used(bp, when=now)
        return JSONResponse({"ok": True, "post": _post_public(post)})


@router.post("/api/bank/fill")
async def api_bank_fill(
    project_id: str = Form(""),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    pid = (project_id or "").strip() or None
    with get_store().mutate() as data:
        created = fill_slots_from_bank(
            data,
            after=datetime.now(MSK),
            days_ahead=21,
            project_id=pid,
        )
    return JSONResponse(
        {
            "ok": True,
            "created": [_post_public(p) for p in created],
            "count": len(created),
        }
    )


@router.post("/api/ai/generate")
async def api_ai_generate(
    project_id: str = Form(...),
    rubric: str = Form("общая"),
    count: int = Form(5),
    extra: str = Form(""),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    proj = project_by_id(project_id)
    if proj is None:
        raise HTTPException(400, "unknown project")
    from publisher.ai_factory import generate_drafts

    drafts, err = generate_drafts(
        persona=proj["persona"],
        rubric=rubric,
        count=count,
        extra=extra,
    )
    if err:
        raise HTTPException(400, err)
    saved = []
    with get_store().mutate() as data:
        data.setdefault("ai_drafts", [])
        for d in drafts:
            row = {
                "id": new_id("aid"),
                "project_id": project_id,
                "title": d.get("title"),
                "body": d.get("body"),
                "category": d.get("category") or "general",
                "status": "pending",
                "created_at": utc_now_iso(),
            }
            data["ai_drafts"].append(row)
            saved.append(row)
        data["ai_drafts"] = data["ai_drafts"][-80:]
    return JSONResponse({"ok": True, "drafts": saved})


@router.post("/api/ai/{draft_id}/accept")
async def api_ai_accept(
    draft_id: str,
    title: str = Form(""),
    body: str = Form(""),
    category: str = Form(""),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    with get_store().mutate() as data:
        drafts = data.get("ai_drafts") or []
        draft = next((d for d in drafts if d.get("id") == draft_id), None)
        if not draft:
            raise HTTPException(404, "draft not found")
        post = new_bank_post(
            project_id=draft["project_id"],
            title=(title or draft.get("title") or ""),
            body=(body or draft.get("body") or ""),
            category=(category or draft.get("category") or "general"),
        )
        data.setdefault("bank_posts", []).append(post)
        draft["status"] = "accepted"
        data["ai_drafts"] = [d for d in drafts if d.get("status") == "pending"]
    return JSONResponse({"ok": True, "bank_post": _bank_public(post)})


@router.post("/api/ai/{draft_id}/reject")
async def api_ai_reject(draft_id: str, empire_studio: str | None = Cookie(default=None)):
    _require(empire_studio)
    with get_store().mutate() as data:
        before = len(data.get("ai_drafts") or [])
        data["ai_drafts"] = [d for d in (data.get("ai_drafts") or []) if d.get("id") != draft_id]
        if len(data["ai_drafts"]) == before:
            raise HTTPException(404, "not found")
    return JSONResponse({"ok": True})


@router.post("/api/bot/settings")
async def api_bot_settings(
    admin_chat_id: str = Form(""),
    digest: str = Form("daily"),
    notify_published: str = Form("1"),
    notify_skipped: str = Form("1"),
    notify_failed: str = Form("1"),
    require_image: str = Form("1"),
    min_body_chars: int = Form(80),
    empire_studio: str | None = Cookie(default=None),
):
    _require(empire_studio)
    notify_on = []
    if notify_published.strip() in ("1", "true", "on", "yes"):
        notify_on.append("published")
    if notify_skipped.strip() in ("1", "true", "on", "yes"):
        notify_on.append("skipped")
    if notify_failed.strip() in ("1", "true", "on", "yes"):
        notify_on.append("failed")
    dig = (digest or "daily").strip().lower()
    if dig not in ("daily", "weekly", "off"):
        dig = "daily"
    with get_store().mutate() as data:
        cur = normalize_bot_settings(data.get("bot_settings"))
        cur["admin_chat_id"] = admin_chat_id.strip()
        cur["digest"] = dig
        cur["notify_on"] = notify_on
        cur["require_image"] = require_image.strip() in ("1", "true", "on", "yes")
        cur["min_body_chars"] = max(20, int(min_body_chars or 80))
        data["bot_settings"] = cur
    return JSONResponse({"ok": True, "bot_settings": cur})


@router.post("/api/bot/ping")
async def api_bot_ping(empire_studio: str | None = Cookie(default=None)):
    _require(empire_studio)
    data = get_store().load()
    settings = normalize_bot_settings(data.get("bot_settings"))
    chat = resolve_admin_chat_id(settings)
    ok, detail = send_admin_text(chat, "[studio] ping — Ops Studio на связи")
    return JSONResponse(
        {
            "ok": ok,
            "detail": detail,
            "chat_id": chat,
            "has_token": bool(telegram_token()),
        }
    )


def _commit_entries(entries: list[dict[str, Any]], *, default_project: str | None) -> list[dict]:
    now = datetime.now(MSK)
    with get_store().mutate() as data:
        placed = assign_next_slots(
            entries,
            data["slots"],
            data["posts"],
            after=now,
            default_project=default_project,
        )
        created: list[dict] = []
        for item in placed:
            if item.get("error"):
                created.append({"error": item["error"], "title": item.get("title")})
                continue
            post = {
                "id": new_id("post"),
                "project_id": item["project_id"],
                "title": item.get("title") or "Без названия",
                "body": item.get("body") or "",
                "image_path": item.get("image_path"),
                "source_filename": item.get("source_filename"),
                "slot_id": item.get("slot_id"),
                "scheduled_at": item.get("scheduled_at"),
                "status": "scheduled",
                "created_at": utc_now_iso(),
                "published_at": None,
                "last_error": None,
            }
            data["posts"].append(post)
            created.append(_post_public(post))
        return created


def _post_public(p: dict) -> dict:
    return {
        "id": p.get("id"),
        "project_id": p.get("project_id"),
        "title": p.get("title"),
        "body": p.get("body"),
        "image_path": p.get("image_path"),
        "image_prompt_en": p.get("image_prompt_en"),
        "bank_id": p.get("bank_id"),
        "category": p.get("category"),
        "rubric_id": p.get("rubric_id"),
        "source_filename": p.get("source_filename"),
        "scheduled_at": p.get("scheduled_at"),
        "status": p.get("status"),
        "created_at": p.get("created_at"),
        "published_at": p.get("published_at"),
        "last_error": p.get("last_error"),
    }


def _bank_public(b: dict) -> dict:
    return {
        "id": b.get("id"),
        "project_id": b.get("project_id"),
        "category": b.get("category"),
        "rubric_id": b.get("rubric_id"),
        "title": b.get("title"),
        "body": b.get("body"),
        "image_path": b.get("image_path"),
        "image_prompt_en": b.get("image_prompt_en"),
        "cooldown_days": b.get("cooldown_days"),
        "times_used": b.get("times_used"),
        "last_used_at": b.get("last_used_at"),
        "status": b.get("status"),
        "created_at": b.get("created_at"),
    }


def _posts_public(posts: list[dict], project_id: str | None) -> list[dict]:
    rows = [_post_public(p) for p in posts if not project_id or p.get("project_id") == project_id]
    rows.sort(key=lambda p: p.get("scheduled_at") or "", reverse=True)
    return rows[:200]


def _status_counts(posts: list[dict], project_id: str | None) -> dict[str, int]:
    out = {
        "scheduled": 0,
        "test_sent": 0,
        "published": 0,
        "failed": 0,
        "skipped": 0,
        "cancelled": 0,
    }
    for p in posts:
        if project_id and p.get("project_id") != project_id:
            continue
        st = p.get("status") or ""
        if st in out:
            out[st] += 1
    return out
