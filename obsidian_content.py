"""Вариант A: посты из Obsidian (queue) → PostDraft → approve в Telegram."""

from __future__ import annotations

import html as html_std
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger("empire.obsidian")

ROOT = Path(__file__).resolve().parent
QUEUE_PATH = ROOT / "data" / "obsidian_import_queue.json"
STATE_PATH = ROOT / "data" / "obsidian_dispatch_state.json"
CONFIG_PATH = ROOT / "data" / "obsidian_config.json"
IMPORT_SCRIPT = ROOT / "scripts" / "import_obsidian_queue.py"

MSK = ZoneInfo("Europe/Moscow")

PERSONA_HASHTAGS = {
    "pension": "#финансы #мысль #экономика",
    "gdepar": "#баня #гдепар #парение",
    "garden": "#огород #дача #урожай",
    "stern": "#штерн #тренировки #спина",
    "lenin": "#ленин #история #мысль",
}


def _load_config() -> dict:
    if CONFIG_PATH.is_file():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {
        "auto_import": True,
        "reminder_hours_before": 2,
        "import_interval_minutes": 10,
    }


def _load_state() -> dict:
    if STATE_PATH.is_file():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
        else:
            # Миграция: dispatched_ids → dispatched {id: scheduled на момент выдачи}
            if "dispatched" not in state and state.get("dispatched_ids"):
                qmap = {e.get("id"): _scheduled_key(e) for e in load_queue() if e.get("id")}
                state["dispatched"] = {
                    eid: qmap.get(eid, "") for eid in state["dispatched_ids"]
                }
            state.setdefault("dispatched", {})
            state.setdefault("reminded", {})
            state.setdefault("dispatched_ids", [])
            state.setdefault("reminded_ids", [])
            return state
    return {
        "dispatched": {},
        "reminded": {},
        "dispatched_ids": [],
        "reminded_ids": [],
        "last_import_at": None,
    }


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_queue() -> list[dict]:
    if not QUEUE_PATH.is_file():
        return []
    try:
        data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    try:
        from scripts.import_obsidian_queue import dedupe_queue_rows

        return dedupe_queue_rows(data)
    except Exception:
        return data


def _resolve_incoming_path() -> Path | None:
    """Каталог импорта queue: env → vault/Empire → obsidian_incoming (если есть .md)."""
    raw = os.environ.get("OBSIDIAN_EMPIRE_INCOMING", "").strip()
    if raw:
        p = Path(raw).expanduser()
        if p.is_dir():
            return p
    vault_empire = ROOT / "data" / "obsidian_vault" / "Empire"
    if vault_empire.is_dir():
        return vault_empire
    incoming = ROOT / "data" / "obsidian_incoming"
    if incoming.is_dir() and any(incoming.rglob("*.md")):
        return incoming
    return None


def run_import_if_needed(force: bool = False) -> bool:
    """Запускает import_obsidian_queue.py при необходимости."""
    cfg = _load_config()
    if not cfg.get("auto_import", True) and not force:
        return False
    incoming_path = _resolve_incoming_path()
    if not incoming_path:
        return False
    state = _load_state()
    interval = int(cfg.get("import_interval_minutes", 10))
    last = state.get("last_import_at")
    if not force and last:
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=MSK)
            if (datetime.now(MSK) - last_dt.astimezone(MSK)).total_seconds() < interval * 60:
                return False
        except ValueError:
            pass
    try:
        env = {**os.environ, "OBSIDIAN_EMPIRE_INCOMING": str(incoming_path)}
        subprocess.run(
            [sys.executable, str(IMPORT_SCRIPT)],
            cwd=str(ROOT),
            check=True,
            timeout=120,
            env=env,
        )
        state["last_import_at"] = datetime.now(MSK).isoformat()
        _save_state(state)
        reconcile_dispatch_state_after_import()
        return True
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("obsidian import failed: %s", exc)
        return False


def parse_scheduled(value: str | None, *, now: datetime | None = None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    now = now or datetime.now(MSK)
    for fmt in (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=MSK)
        except ValueError:
            continue
    return None


def _body_to_html(body: str, fix_html_fn) -> str:
    text = (body or "").strip()
    if not text:
        return ""
    return fix_html_fn(text)


def build_post_html(entry: dict, *, fix_html_fn, finalize_fn) -> str:
    """Сборка поста для Telegram: 📌 заголовок + тело + хештеги (Вариант A)."""
    persona = (entry.get("persona") or "pension").strip().lower()
    title = (entry.get("title") or entry.get("id") or "Пост").strip()
    body_md = entry.get("body_markdown") or ""

    body_html = _body_to_html(body_md, fix_html_fn)
    core = f"📌 <b>{html_std.escape(title)}</b>"
    if body_html:
        core = f"{core}\n\n{body_html}"

    # Рубрика только для topic_raw в БД; в хэштеги — не title (иначе #[Obsidian]"Заголовок").
    is_video = persona == "pension" and "видео" in body_md.lower()
    return finalize_fn(core, persona, "Obsidian", is_video)


def topic_raw_for_entry(entry: dict) -> str:
    return (
        f"[Obsidian] {entry.get('persona', '')} · {entry.get('title', '')} "
        f"(id={entry.get('id', '')})"
    )


def _scheduled_key(entry: dict) -> str:
    return (entry.get("scheduled") or "").strip()


def _is_dispatched(entry: dict, state: dict) -> bool:
    eid = entry.get("id")
    if not eid:
        return True
    dispatched = state.get("dispatched") or {}
    if eid in dispatched:
        return True
    # legacy: id в списке без dispatched{} — считаем отправленным
    return eid in set(state.get("dispatched_ids") or [])


def reconcile_dispatch_state_after_import(queue: list[dict] | None = None) -> int:
    """Снять dispatch с постов, у которых изменился scheduled в frontmatter."""
    queue = queue if queue is not None else load_queue()
    state = _load_state()
    dispatched: dict[str, str] = dict(state.get("dispatched") or {})
    reminded: dict[str, str] = dict(state.get("reminded") or {})
    cleared = 0
    by_id = {e.get("id"): e for e in queue if e.get("id")}
    for eid, old_sched in list(dispatched.items()):
        entry = by_id.get(eid)
        if not entry:
            continue
        if _scheduled_key(entry) != (old_sched or ""):
            dispatched.pop(eid, None)
            reminded.pop(eid, None)
            cleared += 1
    if cleared:
        state["dispatched"] = dispatched
        state["reminded"] = reminded
        state["dispatched_ids"] = list(dispatched.keys())[-500:]
        state["reminded_ids"] = list(reminded.keys())[-500:]
        _save_state(state)
    return cleared


def _eligible_entries(queue: list[dict], state: dict) -> list[dict]:
    reminded = set((state.get("reminded") or {}).keys()) | set(state.get("reminded_ids") or [])
    out: list[dict] = []
    for entry in queue:
        eid = entry.get("id")
        if not eid or _is_dispatched(entry, state):
            continue
        st = (entry.get("status") or "ready").strip().lower()
        if st in ("draft", "published", "cancelled", "template"):
            continue
        entry["_reminded"] = eid in reminded
        out.append(entry)
    return out


def entries_due(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(MSK)
    queue = load_queue()
    state = _load_state()
    due: list[dict] = []
    for entry in _eligible_entries(queue, state):
        sched = parse_scheduled(entry.get("scheduled"))
        if sched and sched <= now:
            due.append(entry)
    return due


def entries_reminder(now: datetime | None = None) -> list[dict]:
    cfg = _load_config()
    hours = float(cfg.get("reminder_hours_before", 2))
    now = now or datetime.now(MSK)
    window_end = now + timedelta(hours=hours)
    queue = load_queue()
    state = _load_state()
    reminded = set(state.get("reminded_ids") or [])
    out: list[dict] = []
    for entry in _eligible_entries(queue, state):
        eid = entry.get("id")
        if eid in reminded:
            continue
        sched = parse_scheduled(entry.get("scheduled"))
        if sched and now < sched <= window_end:
            out.append(entry)
    return out


def mark_dispatched(entry_id: str, *, scheduled: str | None = None) -> None:
    state = _load_state()
    sched = (scheduled or "").strip()
    if not sched:
        for entry in load_queue():
            if entry.get("id") == entry_id:
                sched = _scheduled_key(entry)
                break
    dispatched: dict[str, str] = dict(state.setdefault("dispatched", {}))
    dispatched[entry_id] = sched
    state["dispatched"] = dispatched
    ids = list(state.setdefault("dispatched_ids", []))
    if entry_id not in ids:
        ids.append(entry_id)
    state["dispatched_ids"] = ids[-500:]
    _save_state(state)


def mark_reminded(entry_id: str, *, scheduled: str | None = None) -> None:
    state = _load_state()
    sched = (scheduled or "").strip()
    if not sched:
        for entry in load_queue():
            if entry.get("id") == entry_id:
                sched = _scheduled_key(entry)
                break
    reminded: dict[str, str] = dict(state.setdefault("reminded", {}))
    reminded[entry_id] = sched
    state["reminded"] = reminded
    ids = list(state.setdefault("reminded_ids", []))
    if entry_id not in ids:
        ids.append(entry_id)
    state["reminded_ids"] = ids[-500:]
    _save_state(state)


def _obsidian_image_basename(entry: dict) -> str | None:
    raw = (entry.get("image") or "").strip()
    return Path(raw).name if raw else None


def find_obsidian_image_source(entry: dict) -> Path | None:
    """Ищет файл картинки: рядом с .md, attachments/, по имени в Empire/."""
    raw = (entry.get("image") or "").strip()
    if not raw:
        return None
    basename = Path(raw).name
    seen: set[str] = set()
    candidates: list[Path] = []

    def add(p: Path) -> None:
        key = str(p.resolve()) if p.exists() else str(p)
        if key not in seen:
            seen.add(key)
            candidates.append(p)

    src = Path(raw).expanduser()
    add(src)
    sp = entry.get("source_path")
    if sp:
        md_dir = Path(sp).parent
        add(md_dir / raw)
        add(md_dir / basename)
        add(md_dir / "attachments" / basename)
        for p in md_dir.rglob(basename):
            add(p)
    empire = ROOT / "data" / "obsidian_vault" / "Empire"
    if empire.is_dir():
        for p in empire.rglob(basename):
            if "published" in p.parts:
                continue
            add(p)
    for c in candidates:
        if c.is_file():
            return c
    return None


def copy_obsidian_image(entry: dict, src: Path, *, persona: str, draft_id: int) -> str:
    suffix = src.suffix.lower() if src.suffix else ".jpg"
    if suffix not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        suffix = ".jpg"
    dest = ROOT / "media" / persona / "obsidian" / f"{entry.get('id', draft_id)}{suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(src.read_bytes())
    return str(dest)


def parse_obsidian_entry_id(topic_raw: str | None) -> str | None:
    if not topic_raw:
        return None
    m = re.search(r"\(id=([^)]+)\)", topic_raw)
    return m.group(1).strip() if m else None


def queue_entry_by_id(entry_id: str) -> dict | None:
    for entry in load_queue():
        if entry.get("id") == entry_id:
            return entry
    return None


async def resolve_image_path(entry: dict, generate_image_fn, draft_id: int, persona: str, topic: str) -> str | None:
    """Локальный файл рядом с .md или генерация по image_prompt."""
    src = find_obsidian_image_source(entry)
    if src:
        return copy_obsidian_image(entry, src, persona=persona, draft_id=draft_id)
    if _obsidian_image_basename(entry):
        logger.warning(
            "obsidian image missing for %s: %s",
            entry.get("id"),
            entry.get("image"),
        )
    prompt = (entry.get("image_prompt") or entry.get("title") or "illustration").strip()
    if prompt and generate_image_fn:
        return await generate_image_fn(prompt, draft_id, persona, topic_hint=topic)
    return None


async def resolve_image_for_topic_raw(
    topic_raw: str | None,
    generate_image_fn,
    draft_id: int,
    persona: str,
) -> str | None:
    eid = parse_obsidian_entry_id(topic_raw)
    if not eid:
        return None
    entry = queue_entry_by_id(eid)
    if not entry:
        return None
    return await resolve_image_path(
        entry, generate_image_fn, draft_id, persona, topic_raw or ""
    )
