"""Недельная дуга канала Снегири: программа (пн) → тест (ср) → итоги (вс)."""

from __future__ import annotations

import html as html_std
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

_MSK = ZoneInfo("Europe/Moscow")
_STATE_PATH = Path(__file__).resolve().parent / "data" / "stern_week_state.json"

_WEEKDAY_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
_MONTH_RU = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def _now() -> datetime:
    return datetime.now(_MSK)


def _week_key(when: datetime | None = None) -> str:
    when = when or _now()
    iso = when.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _load_state() -> dict:
    if _STATE_PATH.is_file():
        try:
            return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now().isoformat()
    _STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_week_bucket(state: dict, week: str | None = None) -> dict:
    week = week or _week_key()
    buckets = state.setdefault("weeks", {})
    if week not in buckets:
        buckets[week] = {
            "week": week,
            "plan": None,
            "test": None,
            "posts": [],
        }
    return buckets[week]


def stern_post_url(message_id: int | None) -> str | None:
    """Ссылка на пост в канале Снегири (публичный @ или t.me/c/…)."""
    if not message_id:
        return None
    raw_url = (os.getenv("STERN_TG_URL") or "").strip().rstrip("/")
    if raw_url and "t.me/" in raw_url and "/c/" not in raw_url:
        username = raw_url.split("t.me/")[-1].split("/")[0].split("?")[0].lstrip("@")
        if username:
            return f"https://t.me/{username}/{message_id}"
    chat = (os.getenv("STERN_TG_CHAT_ID") or "-1002024827297").strip()
    inner = chat[4:] if chat.startswith("-100") else chat.lstrip("-")
    return f"https://t.me/c/{inner}/{message_id}"


def _strip_html(text: str) -> str:
    t = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", t).strip()


def _summarize_post(text: str, *, max_len: int = 220) -> str:
    t = _strip_html(text)
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _extract_test_name(text: str) -> str:
    """Название теста из HTML/Markdown поста — без обрезки посередине фразы."""
    plain = _strip_html(text)
    patterns = (
        r"📏\s*Тест\s+недели:\s*(.+?)(?=\s+Крепкий|\s+Сегодня|\s+Как\s+выполнять|\s+Нормы:|\s*$)",
        r"Тест\s+недели:\s*(.+?)(?=\s+—|\s*\.|\s+Сегодня|\s+Как\s+|\s*$)",
        r"\[Тест\s+недели\]\s*(.+)",
    )
    for pat in patterns:
        m = re.search(pat, plain, re.IGNORECASE)
        if m:
            name = m.group(1).strip(" .—–-")
            if name:
                return name
    return ""


def _summary_headline(summary: str, *, max_len: int = 90) -> str:
    s = _summarize_post(summary, max_len=240)
    s = re.sub(r"^[🔥🏋️🧘🩺🛎️🏛️💪🐦🦵🏃🥛🧠🧰]+\s*", "", s)
    if ")" in s:
        idx = s.index(")") + 1
        head = s[:idx].strip()
        if len(head) >= 16:
            return head
    m = re.match(r"^(.+?[.!?])(?:\s|$)", s)
    if m:
        return m.group(1).strip()
    if len(s) > max_len:
        return s[:max_len].rsplit(" ", 1)[0] + "…"
    return s


def _topic_display_label(topic: str, summary: str = "") -> str:
    topic = (topic or "").strip()
    low = topic.lower()
    if "[spy_inspired]" in low or "telethon не подключён" in low:
        return _summary_headline(summary) or "Пост по мотивам разведки"
    m = re.match(r"\[[^\]]+\]\s*(.+)", topic)
    if m:
        label = m.group(1).strip()
        label = re.sub(r"\s*\(id=[^)]+\)\s*$", "", label).strip()
        return label
    return topic[:120] if topic else "Пост"


def _week_range_label(when: datetime) -> str:
    mon = when - timedelta(days=when.weekday())
    sun = mon + timedelta(days=6)
    if mon.month == sun.month:
        return f"{mon.day}–{sun.day} {_MONTH_RU[mon.month]}"
    return f"{mon.day} {_MONTH_RU[mon.month]} – {sun.day} {_MONTH_RU[sun.month]}"


def _link(label: str, url: str | None) -> str:
    safe = html_std.escape(label)
    if url:
        return f'<a href="{html_std.escape(url, quote=True)}">{safe}</a>'
    return f"<b>{safe}</b>"


def record_post(
    *,
    topic: str,
    text: str,
    slot_time: str = "",
    when: datetime | None = None,
    draft_id: int | None = None,
) -> None:
    """Запоминает сгенерированный пост недели для воскресного recap."""
    when = when or _now()
    state = _load_state()
    bucket = _ensure_week_bucket(state, _week_key(when))
    summary = _summarize_post(text, max_len=220)
    bucket["posts"].append(
        {
            "date": when.strftime("%Y-%m-%d"),
            "weekday": _WEEKDAY_RU[when.weekday()],
            "time": slot_time,
            "topic": (topic or "").strip()[:200],
            "summary": summary,
            "label": _topic_display_label(topic, summary),
            "draft_id": draft_id,
            "post_url": None,
        }
    )
    bucket["posts"] = bucket["posts"][-32:]
    _save_state(state)


def mark_post_published(draft_id: int, message_id: int, *, when: datetime | None = None) -> None:
    """После публикации в канал — сохраняем ссылку t.me/… для recap."""
    url = stern_post_url(message_id)
    if not url:
        return
    when = when or _now()
    state = _load_state()
    bucket = _ensure_week_bucket(state, _week_key(when))
    for p in bucket.get("posts") or []:
        if p.get("draft_id") == draft_id:
            p["post_url"] = url
            p["message_id"] = message_id
    plan = bucket.get("plan")
    if plan and plan.get("draft_id") == draft_id:
        plan["post_url"] = url
        plan["message_id"] = message_id
    test = bucket.get("test")
    if test and test.get("draft_id") == draft_id:
        test["post_url"] = url
        test["message_id"] = message_id
    _save_state(state)


def save_weekly_plan(
    *,
    topic: str,
    text: str,
    when: datetime | None = None,
    draft_id: int | None = None,
) -> None:
    when = when or _now()
    state = _load_state()
    bucket = _ensure_week_bucket(state, _week_key(when))
    bucket["plan"] = {
        "posted_at": when.isoformat(),
        "topic": topic,
        "text": text,
        "parsed": _parse_plan_structure(text),
        "draft_id": draft_id,
        "post_url": None,
    }
    _save_state(state)
    record_post(topic=topic, text=text, slot_time="09:30", when=when, draft_id=draft_id)


def save_weekly_test(
    *,
    topic: str,
    text: str,
    when: datetime | None = None,
    draft_id: int | None = None,
) -> None:
    when = when or _now()
    state = _load_state()
    bucket = _ensure_week_bucket(state, _week_key(when))
    bucket["test"] = {
        "posted_at": when.isoformat(),
        "topic": topic,
        "text": text,
        "parsed": _parse_test_structure(text),
        "draft_id": draft_id,
        "post_url": None,
    }
    _save_state(state)
    record_post(topic=topic, text=text, slot_time="15:00", when=when, draft_id=draft_id)


def _parse_plan_structure(text: str) -> dict:
    """Извлекает из плана недели дни и тест — для субботы и воскресенья."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    days: list[dict] = []
    test: dict | None = None
    for ln in lines:
        m_day = re.match(
            r"^(Пн|Вт|Ср|Чт|Пт|Сб|Вс)[:\.\)]\s*(.+)$", ln, re.IGNORECASE
        )
        if m_day:
            days.append({"day": m_day.group(1).capitalize(), "focus": m_day.group(2).strip()})
            continue
        m_test = re.match(r"^(Тест недели|Тест)[:\.\)]\s*(.+)$", ln, re.IGNORECASE)
        if m_test:
            test = {"name": m_test.group(2).strip(), "raw": ln}
    return {"days": days, "test": test}


def _parse_test_structure(text: str) -> dict:
    name = _extract_test_name(text)
    if not name:
        t = _summarize_post(text, max_len=500)
        name = t[:120]
    return {"name": name, "summary": _summarize_post(text, max_len=500)}


def _test_display_name(test: dict) -> str:
    name = _extract_test_name(test.get("text", ""))
    if name:
        return name
    old = (test.get("parsed") or {}).get("name", "")
    if old and len(old) < 100 and not old.endswith("смест"):
        return old
    return "контроль по плану понедельника"


def is_valid_scheduled_post_text(text: str, *, min_plain: int = 200) -> bool:
    """Черновик пригоден для state/recap (не ошибка LLM)."""
    t = (text or "").strip()
    if not t or t.startswith("🛑") or "Ошибка API" in t or t.startswith("Ошибка"):
        return False
    return len(_strip_html(t)) >= min_plain


def weekly_plan_prompt_block(when: datetime | None = None) -> str:
    when = when or _now()
    period = _week_range_label(when)
    return (
        "\nРЕЖИМ «ПРОГРАММА НА НЕДЕЛЮ» — канал «Снегири · здоровый позвоночник»:\n"
        f"• Заголовок: 🔥 Программа недели ({period}).\n"
        "• Фокус: здоровый позвоночник, кор, осанка — по МакГиллу (Big-3: curl-up, side plank, bird dog). "
        "Гири — вспомогательно, не «гиревой спорт».\n"
        "• 6–7 строк «Пн: … Вт: …» — конкретные упражнения, подходы/секунды, вес гири если есть.\n"
        "• Строка перед хэштегами:\n"
        "  Тест недели: [название] — [метрика, выполнить в среду, критерий норма/хорошо]\n"
        "• Без чужих протоколов (Stoppani и т.п.), без выдуманных «уже делали».\n"
    )


def weekly_test_prompt_block(plan_text: str | None, *, when: datetime | None = None) -> str:
    plan_hint = ""
    if plan_text:
        parsed = _parse_plan_structure(plan_text)
        if parsed.get("test"):
            plan_hint = (
                f"Тест из плана понедельника: {parsed['test'].get('name', '')}. "
                "Опиши ТОЛЬКО его — не придумывай другой.\n"
            )
    plan_missing = ""
    if not plan_text:
        plan_missing = (
            "План понедельника в базе не найден — возьми тест «Планка на предплечьях, время до срыва формы» "
            "и явно напиши, что план на неделю не выходил, тест базовый.\n"
        )
    return (
        "\nРЕЖИМ «ТЕСТ НЕДЕЛИ» — СТРОГО:\n"
        + plan_missing
        + "• Заголовок: 📏 Тест недели: [название из плана]\n"
        "• 1 абзац — зачем тест в контексте программы понедельника (ссылайся на пн).\n"
        "• Чек-лист: разминка → выполнение → как записать результат (число/время/повторы).\n"
        "• Критерии «норма / хорошо / отлично» — 3 строки с цифрами.\n"
        "• Без новых тестов, которых не было в плане понедельника.\n"
        + plan_hint
    )


def build_weekly_recap_post(when: datetime | None = None) -> tuple[str, str]:
    """Готовый пост воскресенья — факты из state, без LLM."""
    when = when or _now()
    week = _week_key(when)
    state = _load_state()
    bucket = (state.get("weeks") or {}).get(week) or {}
    plan = bucket.get("plan")
    test = bucket.get("test")
    posts = bucket.get("posts") or []
    period = _week_range_label(when)

    lines = [f"🔥 <b>Итоги недели</b> <i>({period})</i>", ""]

    if not plan:
        lines.append(
            "⚠️ <b>План на понедельник не выходил</b> — сводка без самообмана: "
            "без программы нельзя честно оценить неделю. "
            "Ритм канала: <b>пн 09:30</b> программа → <b>ср 15:00</b> тест → <b>вс 19:00</b> итоги."
        )
    else:
        plan_date = ""
        if plan.get("posted_at"):
            try:
                plan_date = datetime.fromisoformat(plan["posted_at"]).strftime("%d.%m")
            except ValueError:
                pass
        plan_title = _summarize_post(plan.get("text", ""), max_len=180)
        plan_line = f"📋 <b>План недели</b> ({plan_date or 'пн'}): {_link(plan_title, plan.get('post_url'))}"
        lines.append(plan_line)
        parsed = plan.get("parsed") or {}
        if parsed.get("days"):
            lines.append("")
            lines.append("<b>Дни по плану:</b>")
            for d in parsed["days"][:7]:
                lines.append(
                    f"• {html_std.escape(d.get('day', '?'))}: "
                    f"{html_std.escape(d.get('focus', ''))}"
                )
        if parsed.get("test"):
            tn = parsed["test"].get("name", "")
            if tn:
                lines.append("")
                lines.append(f"<b>Тест из плана:</b> {html_std.escape(tn)}")

    if test:
        t_date = ""
        if test.get("posted_at"):
            try:
                t_date = datetime.fromisoformat(test["posted_at"]).strftime("%d.%m")
            except ValueError:
                pass
        test_name = _test_display_name(test)
        lines.append("")
        lines.append(
            f"📏 <b>Тест недели</b> ({t_date or 'ср'}): "
            f"{_link(test_name, test.get('post_url'))}"
        )
        lines.append(
            "<i>Запишите результат и сравните с критериями из поста в среду "
            "(норма / хорошо / отлично).</i>"
        )
    elif plan:
        lines.append("")
        lines.append(
            "<b>Тест недели:</b> пост в среду не выходил — результат не зафиксирован."
        )

    lines.append("")
    lines.append(
        "<b>На следующую неделю:</b> понедельник — новая программа; "
        "среда — тест по ней; воскресенье — снова итоги."
    )

    other = [
        p
        for p in posts
        if not (p.get("topic") or "").startswith("[План на неделю]")
        and "[Тест недели]" not in (p.get("topic") or "")
        and "[Разбор полетов]" not in (p.get("topic") or "")
    ]
    if other:
        lines.append("")
        lines.append("<b>Что ещё выходило в канале:</b>")
        for p in other[-8:]:
            label = p.get("label") or _topic_display_label(
                p.get("topic", ""), p.get("summary", "")
            )
            slot = f"{p.get('weekday', '')} {p.get('time', '')}".strip()
            lines.append(f"• {slot}: {_link(label, p.get('post_url'))}")

    lines.extend(["", "#снегири #позвоночник #итогинедели #макгилл #здоровье"])
    body = "\n".join(lines)
    return "[Разбор полетов] Итоги недели (сводка по плану).", body


def get_current_plan_text() -> str | None:
    bucket = (_load_state().get("weeks") or {}).get(_week_key()) or {}
    plan = bucket.get("plan")
    return (plan or {}).get("text") if plan else None
