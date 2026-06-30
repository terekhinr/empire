"""Tests for health_db."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

import health_db as hd


@pytest.fixture()
def temp_health_db(tmp_path, monkeypatch):
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


def test_seed_and_add_measurement(temp_health_db):
    assert hd.seed_measurements_if_empty() == 1
    assert hd.seed_measurements_if_empty() == 0
    hd.add_measurement(
        "2026-06-16",
        weight_kg=111.1,
        waist_cm=103.5,
        biceps_r_cm=42,
        biceps_l_cm=42,
        legs_cm=66,
    )
    df = hd.load_measurements_df()
    assert len(df) == 2
    summary = hd.latest_measurement_summary()
    assert summary["weight_kg"] == 111.1
    assert summary["waist_cm"] == 103.5


def test_strength_log(temp_health_db):
    hd.add_strength_log("2026-06-16", "bench_press", 100.0, 10, 3)
    df = hd.load_strength_df()
    assert len(df) == 1
    assert df.iloc[0]["exercise_label"] == "Жим штанги лёжа"


def test_import_body_scale_csv(temp_health_db, monkeypatch):
    body_dir = Path(temp_health_db).parent / "body"
    body_dir.mkdir()
    csv = body_dir / "BODY_test.csv"
    csv.write_text(
        "time,weight,height,bmi,fatRate,bodyWaterRate,boneMass,metabolism,muscleRate,visceralFat\n"
        "2016-03-29 03:07:33+0000,102.7,null,null,0.0,0.0,0.0,0.0,0.0,0.0\n"
        "2016-03-30 03:20:59+0000,150.0,null,null,0.0,0.0,0.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(hd, "BODY_DATA_DIR", body_dir)
    result = hd.import_body_scale_csv(csv)
    assert result["imported"] == 1
    conn = sqlite3.connect(temp_health_db)
    n = conn.execute("SELECT COUNT(*) FROM body_scale").fetchone()[0]
    conn.close()
    assert n == 1


def test_measurements_daily_summary(temp_health_db):
    hd.seed_measurements_if_empty()
    daily = hd.measurements_daily_summary()
    assert not daily.empty
    assert "bmi" in daily.columns


def test_sync_csv_if_changed(temp_health_db, monkeypatch):
    body_dir = Path(temp_health_db).parent / "body"
    body_dir.mkdir(parents=True, exist_ok=True)
    csv = body_dir / "BODY_test.csv"
    csv.write_text(
        "time,weight,height,bmi,fatRate,bodyWaterRate,boneMass,metabolism,muscleRate,visceralFat\n"
        "2016-03-29 03:07:33+0000,102.7,null,null,0.0,0.0,0.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )
    (body_dir / "food.csv").write_text("date,calories,protein,fat,carbs\n2024-01-01,2000,100,50,150\n", encoding="utf-8")
    monkeypatch.setattr(hd, "BODY_DATA_DIR", body_dir)
    first = hd.sync_csv_if_changed(force=True)
    assert first is not None
    second = hd.sync_csv_if_changed()
    assert second is None
    csv.write_text(
        csv.read_text(encoding="utf-8")
        + "2016-03-30 03:20:59+0000,103.0,null,null,0.0,0.0,0.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )
    third = hd.sync_csv_if_changed()
    assert third is not None


def test_sanitize_weight_and_smooth():
    assert hd.sanitize_weight(111.0) == 111.0
    assert hd.sanitize_weight(85.0) is None
    assert hd.sanitize_weight(125.0) is None
    s = pd.Series([100.0, 102.0, 104.0, 103.0, 101.0])
    smooth = hd.smooth_series(s, window=3)
    assert len(smooth) == 5
    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "weight_kg": [100.0, 150.0, 102.0]})
    out = hd.prepare_chart_frame(df, smooth_cols=["weight_kg"], weight_cols=["weight_kg"])
    assert out.loc[1, "weight_kg"] is None or pd.isna(out.loc[1, "weight_kg"])
    assert "weight_kg_smooth" in out.columns
