"""Аварийные стопы дашборда (ТЗ FINAL §9). Файл data/empire_flags.json."""

from __future__ import annotations

import json
from pathlib import Path

_FLAGS_PATH = Path(__file__).resolve().parent / "data" / "empire_flags.json"
_DEFAULTS = {
    "stop_publications": False,
    "stop_neurocomment": True,
    "stop_scout": False,
    "stop_spy": True,
    "stop_sales": True,
    "stop_worker": False,
}


def load_empire_flags() -> dict:
    if not _FLAGS_PATH.is_file():
        return dict(_DEFAULTS)
    try:
        raw = json.loads(_FLAGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)
    out = dict(_DEFAULTS)
    if isinstance(raw, dict):
        for k in _DEFAULTS:
            if k in raw:
                out[k] = bool(raw[k])
    return out


def save_empire_flags(flags: dict) -> None:
    out = dict(_DEFAULTS)
    for k in _DEFAULTS:
        if k in flags:
            out[k] = bool(flags[k])
    _FLAGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FLAGS_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
