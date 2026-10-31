"""Zip backup of health.db + uploaded workout programs."""

from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path

from health_db import HEALTH_DB_PATH, HEALTH_DIR
from health_workout_program import USER_PROGRAMS_DIR

BACKUPS_DIR = HEALTH_DIR / "backups"
KEEP = 14


def create_health_backup() -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUPS_DIR / f"health_{stamp}.zip"
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if HEALTH_DB_PATH.is_file():
            zf.write(HEALTH_DB_PATH, arcname="health.db")
        if USER_PROGRAMS_DIR.is_dir():
            for path in USER_PROGRAMS_DIR.rglob("*"):
                if path.is_file():
                    zf.write(path, arcname=str(Path("programs") / path.relative_to(USER_PROGRAMS_DIR)))
    zips = sorted(BACKUPS_DIR.glob("health_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in zips[KEEP:]:
        old.unlink(missing_ok=True)
    return dest
