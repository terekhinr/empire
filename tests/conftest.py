"""Общая настройка тестов: корень проекта и URL БД для gdepar."""

from __future__ import annotations

import json
import os
import sys

import pytest

# Не тянуть sentence-transformers с HuggingFace при импорте main (pytest/CI/песочница).
os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///empire.db")


@pytest.fixture()
def temp_health_db(tmp_path, monkeypatch):
    import health_db as hd

    db_dir = tmp_path / "health"
    db_dir.mkdir()
    db_path = db_dir / "health.db"
    seed_path = db_dir / "measurements_seed.json"
    seed_path.write_text(
        json.dumps(
            [
                {
                    "date": "2025-01-01",
                    "biceps_r_cm": 41,
                    "biceps_l_cm": 40,
                    "waist_cm": 100,
                    "legs_cm": 64,
                    "weight_kg": 108.0,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hd, "HEALTH_DIR", db_dir)
    monkeypatch.setattr(hd, "HEALTH_DB_PATH", db_path)
    monkeypatch.setattr(hd, "SEED_PATH", seed_path)
    hd.init_db()
    yield db_path
