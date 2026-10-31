"""JSON-хранилище издательства. Один файл, без БД."""

from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from publisher.notify import DEFAULT_BOT_SETTINGS

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORE_PATH = ROOT / "data" / "publisher" / "store.json"
CONTENT_CONFIG_PATH = ROOT / "content_config.json"

_EMPTY = {
    "version": 3,
    "mode": "test",
    "slots": [],
    "posts": [],
    "outbox": [],
    "bank_posts": [],
    "ai_drafts": [],
    "rubrics": [],
    "bot_settings": dict(DEFAULT_BOT_SETTINGS),
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


class Store:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_STORE_PATH

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            data = deepcopy(_EMPTY)
            self._seed_slots(data)
            self.save(data)
            return data
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = deepcopy(_EMPTY)
            self._seed_slots(data)
            self.save(data)
            return data
        if not isinstance(raw, dict):
            data = deepcopy(_EMPTY)
            self._seed_slots(data)
            self.save(data)
            return data
        self._normalize(raw)
        seeded = False
        if not raw["slots"]:
            self._seed_slots(raw)
            seeded = True
        before_r = len(raw.get("rubrics") or [])
        before_s = len(raw.get("slots") or [])
        self._ensure_pilot(raw)
        if seeded or len(raw.get("rubrics") or []) != before_r or len(raw.get("slots") or []) != before_s:
            self.save(raw)
        return raw

    def _normalize(self, raw: dict[str, Any]) -> None:
        raw.setdefault("version", 3)
        raw.setdefault("mode", "test")
        raw.setdefault("slots", [])
        raw.setdefault("posts", [])
        raw.setdefault("outbox", [])
        raw.setdefault("bank_posts", [])
        raw.setdefault("ai_drafts", [])
        raw.setdefault("rubrics", [])
        if not isinstance(raw.get("bot_settings"), dict):
            raw["bot_settings"] = dict(DEFAULT_BOT_SETTINGS)
        else:
            merged = dict(DEFAULT_BOT_SETTINGS)
            merged.update(raw["bot_settings"])
            raw["bot_settings"] = merged

    def save(self, data: dict[str, Any]) -> None:
        self._ensure_parent()
        self._normalize(data)
        self._ensure_pilot(data)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, self.path)

    def _ensure_pilot(self, data: dict[str, Any]) -> None:
        from publisher.rubrics import ensure_garden_slots, ensure_rubrics

        ensure_rubrics(data)
        ensure_garden_slots(data)

    def _seed_slots(self, data: dict[str, Any]) -> None:
        from publisher.catalog import seed_slots_from_content_config

        cfg: dict = {}
        if CONTENT_CONFIG_PATH.is_file():
            try:
                cfg = json.loads(CONTENT_CONFIG_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                cfg = {}
        data["slots"] = seed_slots_from_content_config(cfg)
        self._ensure_pilot(data)

    def mutate(self) -> "_Txn":
        return _Txn(self)


class _Txn:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.data: dict[str, Any] | None = None

    def __enter__(self) -> dict[str, Any]:
        self.data = self.store.load()
        return self.data

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None and self.data is not None:
            self.store.save(self.data)
