#!/usr/bin/env python3
"""Classify voice transcripts and build Obsidian notes with routing metadata."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Route:
    id: str
    label: str
    vault_path: str
    book: str | None
    project: str | None
    kind: str
    tags: tuple[str, ...]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_config_path() -> Path:
    env = os.environ.get("VOICE_ROUTE_CONFIG")
    if env:
        return Path(env)
    return repo_root() / "data" / "voice_route_config.json"


def load_config(path: Path | None = None) -> dict:
    cfg_path = path or default_config_path()
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def _route_from_entry(entry: dict) -> Route:
    return Route(
        id=entry["id"],
        label=entry.get("label", entry["id"]),
        vault_path=entry["vault_path"],
        book=entry.get("book"),
        project=entry.get("project"),
        kind=entry.get("kind", "inbox"),
        tags=tuple(entry.get("tags", ["voice"])),
    )


def _matches(route_entry: dict, filename: str, text: str) -> bool:
    hay = f"{filename}\n{text[:800]}"
    for pat in route_entry.get("patterns", []):
        if re.search(pat, hay, re.I | re.MULTILINE):
            return True
    for pat in route_entry.get("filename_patterns", []):
        if re.search(pat, filename, re.I):
            return True
    return False


def classify(filename: str, text: str, config: dict | None = None) -> Route:
    cfg = config or load_config()
    for entry in cfg.get("routes", []):
        if _matches(entry, filename, text):
            return _route_from_entry(entry)
    return _route_from_entry(cfg["default"])


def audio_wikilink(note_vault_path: str, audio_name: str, audio_vault_path: str) -> str:
    """Relative wikilink from note folder to central audio storage."""
    note_dir = Path(note_vault_path)
    audio_file = Path(audio_vault_path) / audio_name
    rel = os.path.relpath(audio_file, note_dir).replace("\\", "/")
    return f"[[{rel}]]"


def _yaml_list(items: tuple[str, ...]) -> str:
    if not items:
        return "[]"
    if len(items) == 1:
        return f"[{items[0]}]"
    lines = "\n".join(f"  - {t}" for t in items)
    return f"\n{lines}"


def _yaml_optional(key: str, value: str | None) -> str:
    if value is None:
        return ""
    return f"{key}: {value}\n"


def strip_routing_prefix(text: str, config: dict | None = None) -> str:
    """Drop a short spoken routing phrase from the start of the transcript."""
    cfg = config or load_config()
    lines = text.strip().split("\n")
    first_line = lines[0].strip() if lines else ""
    if len(first_line) > 120:
        return text
    for entry in cfg.get("routes", []):
        for pat in entry.get("patterns", []):
            m = re.search(pat, first_line, re.I)
            if not m:
                continue
            after = first_line[m.end() :].lstrip(".,:;—–- ")
            tail = "\n".join(lines[1:]).strip()
            if after:
                return f"{after}\n{tail}".strip() if tail else after
            return tail or text
    return text


def write_voice_note(
    dest_dir: Path,
    *,
    route: Route,
    audio_name: str,
    text: str,
    stamp: datetime,
    audio_vault_path: str,
) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{stamp.strftime('%Y-%m-%d-%H%M')}-voice-{route.id}.md"
    out = dest_dir / fname
    if out.exists():
        out = dest_dir / f"{stamp.strftime('%Y-%m-%d-%H%M%S')}-voice-{route.id}.md"

    body_text = strip_routing_prefix(text)
    link = audio_wikilink(route.vault_path, audio_name, audio_vault_path)
    tags_yaml = _yaml_list(route.tags)
    if tags_yaml.startswith("\n"):
        tags_block = f"tags:{tags_yaml}"
    else:
        tags_block = f"tags: {tags_yaml}"

    body = f"""---
date: {stamp.strftime("%Y-%m-%d")}
source: voice
route: {route.id}
{_yaml_optional("book", route.book)}{_yaml_optional("project", route.project)}kind: {route.kind}
audio: "{link}"
{tags_block}
---

## {route.label}

## Транскрипт

{body_text}

## Действия

- [ ]
"""
    out.write_text(body, encoding="utf-8")
    return out


def push_paths(config: dict | None = None) -> list[str]:
    cfg = config or load_config()
    return list(cfg.get("push_paths", []))
