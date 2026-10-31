"""SSR «Личный Практикум» — Codecademy-style path без SPA (для ПК/телефона)."""
from __future__ import annotations

import html as html_lib
import os
import secrets
from typing import Any

# Порядок курса = силлабус (как Codecademy Career Path)
COURSE_ORDER: list[tuple[str, str, str, str]] = [
    # ref, title, window, est
    ("lms-sem1-w00", "Неделя 0 · Онбординг", "22–26 окт 2026", "~3 ч"),
    ("lms-sem1-w01", "Неделя 1 · Python: типы и ветвления", "27 окт – 2 ноя", "4–5 ч"),
    ("lms-sem1-w02", "Неделя 2 · Циклы, функции, списки", "3–9 ноя", "4–5 ч"),
    ("lms-sem1-w03", "Неделя 3 · Словари + To-Do CLI", "10–16 ноя", "4–5 ч"),
    ("lms-sem1-w04", "Неделя 4 · Git + критерий M1", "17–23 ноя", "4–5 ч"),
    ("lms-sem1-w05", "Неделя 5 · Aiogram quickstart", "24–30 ноя", "4–5 ч"),
    ("lms-sem1-w06", "Неделя 6 · Echo-бот", "1–7 дек", "4–5 ч"),
    ("lms-sem1-w07", "Неделя 7 · FSM анкета", "8–14 дек", "4–5 ч"),
    ("lms-sem1-w08", "Неделя 8 · /cancel + критерий M2", "15–21 дек", "4–5 ч"),
    ("lms-sem1-w09", "Неделя 9 · SQL основы", "22–28 дек", "4–5 ч"),
    ("lms-sem1-w10", "Неделя 10 · SQLite leads", "29 дек – 4 янв", "4–5 ч"),
    ("lms-sem1-w11", "Неделя 11 · SQLAlchemy 2.0", "5–11 янв 2027", "4–5 ч"),
    ("lms-sem1-w12", "Неделя 12 · КТ-1 · память в БД", "12–18 янв", "4–5 ч"),
    ("lms-sem1-w13", "Неделя 13 · Docker основы", "19–25 янв", "4–5 ч"),
    ("lms-sem1-w14", "Неделя 14 · Compose + Postgres", "26 янв – 1 фев", "4–5 ч"),
    ("lms-sem1-w15", "Неделя 15 · Sheets + логи", "2–8 фев", "4–5 ч"),
    ("lms-sem1-w16", "Неделя 16 · КТ-2 · диплом Lead Bot", "9–15 фев", "5–6 ч"),
]

COOKIE = "empire_go_tasks_token"


def _expected_token() -> str:
    return (os.getenv("PLANNING_API_TOKEN") or "").strip()


def token_ok(t: str) -> bool:
    exp = _expected_token()
    t = (t or "").strip()
    return bool(exp) and bool(t) and secrets.compare_digest(t, exp)


def load_course(token: str) -> dict[str, Any]:
    """Собирает силлабус + прогресс из чеклистов lms-sem1-* (прямо из DB)."""
    if not token_ok(token):
        return {"error": "auth", "lessons": [], "pct": 0, "continue": None}
    try:
        from planning_db import find_checklist_by_ref, get_checklist
    except Exception as e:
        return {"error": str(e)[:160], "lessons": [], "pct": 0, "continue": None}

    lessons: list[dict[str, Any]] = []
    total = done = 0
    continue_ref: str | None = None
    continue_id: int | None = None

    for ref, title, window, est in COURSE_ORDER:
        cl = find_checklist_by_ref(ref)
        if not cl or cl.get("status") == "archived":
            lessons.append(
                {
                    "ref": ref,
                    "title": title,
                    "window": window,
                    "est": est,
                    "id": None,
                    "done": 0,
                    "total": 0,
                    "pct": 0,
                    "missing": True,
                }
            )
            if continue_ref is None:
                continue_ref = ref
            continue
        cid = int(cl["id"])
        detail = get_checklist(cid) or cl
        items = detail.get("items") if isinstance(detail, dict) else []
        if not isinstance(items, list):
            items = []
        td = len(items)
        dn = sum(1 for i in items if isinstance(i, dict) and i.get("status") == "done")
        total += td
        done += dn
        pct = int(round(100 * dn / td)) if td else 0
        lessons.append(
            {
                "ref": ref,
                "title": title,
                "window": window,
                "est": est,
                "id": cid,
                "done": dn,
                "total": td,
                "pct": pct,
                "missing": False,
                "items": items,
            }
        )
        if continue_ref is None and pct < 100:
            continue_ref = ref
            continue_id = cid

    pct_all = int(round(100 * done / total)) if total else 0
    cont = next((L for L in lessons if L["ref"] == continue_ref), None)
    return {
        "error": None,
        "lessons": lessons,
        "pct": pct_all,
        "done": done,
        "total": total,
        "continue": cont,
        "continue_id": continue_id,
    }


def toggle_item(token: str, checklist_id: int, item_id: int, status: str) -> str | None:
    """status: done|todo. Returns error string or None."""
    if not token_ok(token):
        return "auth"
    try:
        from planning_db import get_checklist, update_checklist_item_status

        cl = get_checklist(checklist_id)
        if not cl:
            return "checklist_not_found"
        if not any(int(i["id"]) == item_id for i in cl.get("items", [])):
            return "item_not_found"
        update_checklist_item_status(item_id, status)
        return None
    except Exception as e:
        return str(e)[:120]


def render_hub() -> str:
    return f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">
<title>Empire · вход</title>
<style>
html,body{{margin:0;min-height:100%;background:#0b1220;color:#e2e8f0;font-family:system-ui,sans-serif}}
#wrap{{max-width:560px;margin:0 auto;padding:28px 16px 48px}}
h1{{margin:0 0 6px;font-size:1.75rem;color:#ffe600}}
.sub{{color:#94a3b8;margin:0 0 22px;line-height:1.45}}
a.card{{display:block;text-decoration:none;color:inherit;background:#111827;border:1px solid #334155;
  border-radius:14px;padding:16px 16px;margin:0 0 12px}}
a.card strong{{display:block;font-size:1.15rem;color:#ffe600;margin-bottom:4px}}
a.card span{{color:#cbd5e1;font-size:0.92rem;line-height:1.4}}
a.card.gym strong{{color:#38bdf8}}
a.card.learn strong{{color:#4ade80}}
a.card.reset strong{{color:#fbbf24}}
</style></head><body><div id="wrap">
<h1>Empire</h1>
<p class="sub">Один вход. Не открывай старую иконку /tasks/. Завтра на тренировку — «Зал».</p>
<a class="card" href="/go-tasks/"><strong>Задачник</strong><span>Список задач (без чёрного экрана). Токен → список.</span></a>
<a class="card gym" href="/gym/"><strong>Зал</strong><span>Программа, дневник, замеры — для тренировки.</span></a>
<a class="card learn" href="/go-learn/"><strong>Практикум</strong><span>Семестр 1 · прогресс · недели · Continue.</span></a>
<a class="card reset" href="/go-reset/"><strong>Сброс кэша</strong><span>Если снова чёрный экран — сюда, потом Задачник.</span></a>
</div>
<script>
try{{if(navigator.serviceWorker)navigator.serviceWorker.getRegistrations().then(function(rs){{rs.forEach(function(r){{r.unregister()}})}})}}catch(e){{}}
</script>
</body></html>"""


def render_learn(
    *,
    course: dict[str, Any] | None = None,
    authed: bool = False,
    err: str | None = None,
    open_id: int | None = None,
    token: str | None = None,
) -> str:
    e = html_lib.escape
    if not authed:
        return f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">
<title>Практикум · вход</title>
<style>
html,body{{margin:0;background:#0b1220;color:#e2e8f0;font-family:system-ui,sans-serif;min-height:100%}}
#wrap{{max-width:520px;margin:0 auto;padding:28px 16px}}
h1{{color:#4ade80;margin:0 0 8px}}
.card{{background:#111827;border-radius:14px;padding:18px;border:1px solid #334155}}
input{{width:100%;box-sizing:border-box;padding:12px;border-radius:10px;border:1px solid #475569;background:#020617;color:#fff}}
button{{margin-top:12px;padding:12px 18px;border:0;border-radius:10px;background:#4ade80;color:#052e16;font-weight:800;font-size:1.05rem}}
.err{{color:#fbbf24;margin:8px 0}}
a{{color:#93c5fd}}
</style></head><body><div id="wrap">
<p><a href="/go/">← Empire</a></p>
<h1>Практикум</h1>
<div class="card">
<p>Тот же токен, что в Задачнике.</p>
<form method="post" action="/go-learn/">
<label>Токен</label>
<input name="token" type="password" required autofocus>
<div class="err">{e(err or "")}</div>
<button type="submit">ВОЙТИ В КУРС</button>
</form>
</div></div></body></html>"""

    assert course is not None
    if course.get("error"):
        body = f'<div class="err">API: {e(str(course["error"]))}</div>'
    else:
        pct = int(course.get("pct") or 0)
        cont = course.get("continue")
        cont_html = ""
        if cont and cont.get("id"):
            cont_html = f"""
<div class="continue">
  <div class="label">Продолжить с места остановки</div>
  <a class="btn-cont" href="/go-learn/?open={int(cont['id'])}">{e(cont['title'])}</a>
  <div class="meta">{e(cont.get('window') or '')} · {e(cont.get('est') or '')} · {int(cont.get('pct') or 0)}%</div>
</div>"""
        elif cont and cont.get("missing"):
            cont_html = """
<div class="continue"><div class="label">Курс ещё не засеян</div>
<p class="meta">На сервере: <code>./venv/bin/python scripts/seed_practicum_lms_2026.py --force</code></p></div>"""

        lessons_html = []
        for L in course.get("lessons") or []:
            cid = L.get("id")
            active = open_id and cid and int(cid) == int(open_id)
            bar = int(L.get("pct") or 0)
            status = "missing" if L.get("missing") else ("done" if bar >= 100 else "open")
            head = f"""
<div class="lesson {status}{' active' if active else ''}">
  <a class="ltitle" href="{'/go-learn/?open='+str(cid) if cid else '/go-learn/'}">
    <span>{e(L['title'])}</span>
    <span class="pct">{bar}%</span>
  </a>
  <div class="meta">{e(L.get('window') or '')} · {e(L.get('est') or '')} · {int(L.get('done') or 0)}/{int(L.get('total') or 0)}</div>
  <div class="bar"><i style="width:{bar}%"></i></div>"""
            items_html = ""
            if active and L.get("items"):
                bits = []
                for it in L["items"]:
                    if not isinstance(it, dict):
                        continue
                    iid = int(it["id"])
                    done = it.get("status") == "done"
                    next_st = "todo" if done else "done"
                    chk = "✓" if done else "○"
                    bits.append(
                        f"""<form method="post" action="/go-learn/" class="item{' done' if done else ''}">
<input type="hidden" name="action" value="toggle">
<input type="hidden" name="checklist_id" value="{cid}">
<input type="hidden" name="item_id" value="{iid}">
<input type="hidden" name="status" value="{next_st}">
<input type="hidden" name="open" value="{cid}">
<button type="submit"><span class="chk">{chk}</span> {e(str(it.get('title') or ''))}</button>
</form>"""
                    )
                items_html = '<div class="items">' + "".join(bits) + "</div>"
            lessons_html.append(head + items_html + "</div>")

        body = f"""
<div class="progress-card">
  <div class="path">B2B Python Developer · Семестр 1</div>
  <div class="big">{pct}%</div>
  <div class="meta">{int(course.get('done') or 0)} / {int(course.get('total') or 0)} шагов</div>
  <div class="bar big"><i style="width:{pct}%"></i></div>
</div>
{cont_html}
<div class="syllabus"><h2>Силлабус</h2>{''.join(lessons_html)}</div>
"""

    title_pct = "—"
    if course and not course.get("error"):
        title_pct = str(int(course.get("pct") or 0))
    return f"""<!DOCTYPE html>
<html lang="ru"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache,no-store,must-revalidate">
<title>Практикум · {title_pct}%</title>
<style>
html,body{{margin:0;background:#0b1220;color:#e2e8f0;font-family:system-ui,sans-serif}}
#wrap{{max-width:720px;margin:0 auto;padding:18px 14px 56px}}
a{{color:#93c5fd;text-decoration:none}}
.nav{{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 16px;font-size:0.9rem}}
.progress-card{{background:#111827;border:1px solid #334155;border-radius:16px;padding:16px;margin:0 0 14px}}
.path{{color:#4ade80;font-weight:700;margin-bottom:6px}}
.big{{font-size:2.4rem;font-weight:800;line-height:1}}
.meta{{color:#94a3b8;font-size:0.88rem;margin-top:6px}}
.bar{{height:8px;background:#1e293b;border-radius:99px;overflow:hidden;margin-top:10px}}
.bar.big{{height:12px}}
.bar i{{display:block;height:100%;background:linear-gradient(90deg,#22c55e,#4ade80);width:0}}
.continue{{background:#052e16;border:1px solid #166534;border-radius:14px;padding:14px;margin:0 0 16px}}
.continue .label{{color:#86efac;font-size:0.85rem;margin-bottom:8px}}
.btn-cont{{display:inline-block;background:#4ade80;color:#052e16;font-weight:800;padding:12px 16px;border-radius:10px}}
h2{{font-size:1.05rem;margin:18px 0 10px;color:#cbd5e1}}
.lesson{{background:#111827;border:1px solid #334155;border-radius:12px;padding:12px;margin:0 0 10px}}
.lesson.done{{opacity:0.72}}
.lesson.missing{{border-style:dashed}}
.lesson.active{{border-color:#4ade80}}
.ltitle{{display:flex;justify-content:space-between;gap:10px;color:#f8fafc;font-weight:650}}
.pct{{color:#4ade80}}
.items{{margin-top:10px}}
.item button{{width:100%;text-align:left;background:#0f172a;color:#e2e8f0;border:1px solid #334155;
  border-radius:10px;padding:10px 12px;margin:0 0 6px;cursor:pointer;font-size:0.95rem}}
.item.done button{{color:#86efac;border-color:#166534}}
.chk{{display:inline-block;width:1.2em}}
.err{{color:#fbbf24}}
.logout{{margin-left:auto}}
</style></head><body><div id="wrap">
<nav class="nav">
  <a href="/go/">Empire</a>
  <a href="/go-tasks/">Задачник</a>
  <a href="/gym/">Зал</a>
  <a href="/go-learn/">Практикум</a>
  <form method="post" action="/go-learn/" class="logout" style="margin:0">
    <input type="hidden" name="action" value="logout">
    <button type="submit" style="background:transparent;border:0;color:#94a3b8;cursor:pointer">Выйти</button>
  </form>
</nav>
{body}
<p class="meta" style="margin-top:24px">Канон: docs/career_curriculum_b2b_2026-10.md · UX: Codecademy path (прогресс по урокам) + структура Практикума.</p>
</div>
<script>
try{{if(navigator.serviceWorker)navigator.serviceWorker.getRegistrations().then(function(rs){{rs.forEach(function(r){{r.unregister()}})}})}}catch(e){{}}
</script>
</body></html>"""
