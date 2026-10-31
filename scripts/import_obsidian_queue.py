#!/usr/bin/env python3
"""
Импорт Markdown из Obsidian (или любой папки) в очередь Empire.

Ожидается YAML frontmatter между --- ... --- (простые поля key: value).
Переменная окружения OBSIDIAN_EMPIRE_INCOMING — корень обхода (рекурсивно *.md).

Выход: data/obsidian_import_queue.json

Пример:
  export OBSIDIAN_EMPIRE_INCOMING=~/Vault/Empire/pension/queue
  ./venv/bin/python scripts/import_obsidian_queue.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUT = ROOT / "data" / "obsidian_import_queue.json"


def _strip_yaml_scalar(val: str) -> str:
    """Снимает вложенные кавычки: '\"текст\"' → текст."""
    val = val.strip()
    while len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        val = val[1:-1].strip()
    return val


def _parse_simple_yaml_block(block: str) -> dict[str, str]:
    """Только плоские key: value без вложенности."""
    meta: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        key = key.strip()
        meta[key] = _strip_yaml_scalar(rest)
    return meta


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    fm_raw = parts[1].strip()
    body = parts[2].strip()
    return _parse_simple_yaml_block(fm_raw), body


SKIP_DIR_NAMES = frozenset(
    {
        "published",
        "inbox",
        ".obsidian",
        "_canvas",
        "_scenarios",
        "_canon",
        "_finance",
        "journal",
        "templates",
        "_templates",
        "_reviews",
    }
)
# Любой сегмент пути *_templates (в т.ч. pension/_templates)
PERSONA_DIRS = frozenset({"pension", "gdepar", "garden", "stern", "lenin"})
SKIP_FILE_NAMES = frozenset({"_template.md", "readme.md"})

_STATUS_RANK = {"ready": 0, "draft": 1, "published": 2, "cancelled": 3, "template": 4}


def _row_rank(row: dict) -> tuple:
    st = (row.get("status") or "ready").strip().lower()
    rank = _STATUS_RANK.get(st, 9)
    body = row.get("body_markdown") or ""
    return (rank, -len(body))


def dedupe_queue_rows(rows: list[dict]) -> list[dict]:
    """Один id — одна запись (иначе бот шлёт черновик по кругу)."""
    by_id: dict[str, dict] = {}
    paths_by_id: dict[str, list[str]] = {}
    for row in rows:
        eid = (row.get("id") or "").strip()
        if not eid:
            continue
        paths_by_id.setdefault(eid, []).append(row.get("source_path", "?"))
        prev = by_id.get(eid)
        if prev is None or _row_rank(row) < _row_rank(prev):
            by_id[eid] = row
    for eid, paths in paths_by_id.items():
        if len(paths) > 1:
            keep = by_id[eid].get("source_path", "?")
            print(
                f"WARN: duplicate id={eid!r} in queue/ ({len(paths)} files) — "
                f"keeping {keep}; fix id: in other .md files",
                file=sys.stderr,
            )
    return [by_id[k] for k in sorted(by_id)]


def _infer_persona(path: Path, incoming: Path, meta: dict[str, str]) -> str:
    explicit = (meta.get("persona") or "").strip().lower()
    if explicit:
        return explicit
    try:
        rel = path.relative_to(incoming)
        if rel.parts and rel.parts[0] in PERSONA_DIRS:
            return rel.parts[0]
    except ValueError:
        pass
    return "pension"


def walk_md(root: Path) -> list[Path]:
    """Импорт только из `persona/queue/` при корне Empire; иначе рекурсивно (legacy)."""
    if any((root / name).is_dir() for name in PERSONA_DIRS):
        out: list[Path] = []
        for persona in sorted(PERSONA_DIRS):
            queue = root / persona / "queue"
            if not queue.is_dir():
                continue
            for p in sorted(queue.glob("*.md")):
                if p.name.startswith("."):
                    continue
                if p.name.lower() in SKIP_FILE_NAMES:
                    continue
                out.append(p)
        return out

    out = []
    for p in root.rglob("*.md"):
        if p.name.startswith("."):
            continue
        if p.name.lower() in SKIP_FILE_NAMES:
            continue
        if any(part in SKIP_DIR_NAMES or part.endswith("_templates") for part in p.parts):
            continue
        out.append(p)
    return sorted(out)


def main() -> int:
    env_raw = os.environ.get("OBSIDIAN_EMPIRE_INCOMING", "").strip()
    incoming = (ROOT / "data" / "obsidian_incoming").resolve()
    if env_raw:
        incoming = Path(env_raw).expanduser().resolve()
    if not incoming.is_dir():
        print(f"Нет каталога: {incoming}", file=sys.stderr)
        print("Создайте data/obsidian_incoming/ или задайте OBSIDIAN_EMPIRE_INCOMING", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for path in walk_md(incoming):
        raw = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(raw)
        stem = path.stem
        eid = (meta.get("id") or stem).strip()
        persona = _infer_persona(path, incoming, meta)
        title = (meta.get("title") or stem.replace("-", " ")).strip()
        scheduled = (meta.get("scheduled") or meta.get("publish_at") or "").strip()
        status = (meta.get("status") or "ready").strip().lower()
        rows.append(
            {
                "id": eid,
                "source_path": str(path),
                "persona": persona,
                "title": title,
                "body_markdown": body,
                "scheduled": scheduled or None,
                "status": status,
                "image": (meta.get("image") or "").strip() or None,
                "image_prompt": (meta.get("image_prompt") or meta.get("image_prompt_en") or "").strip() or None,
                "skip_image": (meta.get("skip_image") or "").strip().lower() in {"1", "true", "yes", "on"},
                "imported_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    rows = dedupe_queue_rows(rows)

    OUT = Path(os.environ.get("OBSIDIAN_IMPORT_QUEUE_OUT", str(DEFAULT_OUT))).expanduser().resolve()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not rows and OUT.is_file():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = []
        if prev:
            print(
                f"WARN: 0 notes из {incoming} — очередь не трогаем ({len(prev)} записей)",
                file=sys.stderr,
            )
            return 0
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        import obsidian_content as oc

        n = oc.reconcile_dispatch_state_after_import(rows)
        if n:
            print(f"  сброшен dispatch у {n} постов (изменился scheduled)")
    except Exception as exc:
        print(f"  warn: reconcile dispatch: {exc}", file=sys.stderr)
    print(f"OK {len(rows)} notes → {OUT} (from {incoming})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
