"""Удаление старых файлов media/ (ТЗ §4.1 garbage collector)."""

from __future__ import annotations

import os
import time
from pathlib import Path

MEDIA_DIR = Path(__file__).resolve().parent / "media"
DEFAULT_TTL_DAYS = int(os.getenv("EMPIRE_MEDIA_TTL_DAYS", "45"))


def run_media_gc(*, ttl_days: int | None = None, dry_run: bool = False) -> int:
    ttl = ttl_days if ttl_days is not None else DEFAULT_TTL_DAYS
    if not MEDIA_DIR.is_dir():
        return 0
    cutoff = time.time() - ttl * 86400
    deleted = 0
    for path in MEDIA_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.name.endswith(".blacklist.txt"):
            continue
        try:
            if path.stat().st_mtime < cutoff:
                if not dry_run:
                    path.unlink(missing_ok=True)
                deleted += 1
        except OSError:
            continue
    return deleted
