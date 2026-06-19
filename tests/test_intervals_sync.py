"""Tests for intervals_sync and Intervals import helpers."""

from __future__ import annotations

import health_db as hd
import intervals_sync as icu


def test_import_intervals_activities(temp_health_db):
    activities = [
        {
            "id": 101,
            "type": "Run",
            "name": "Morning run",
            "start_date_local": "2026-06-15T07:30:00",
            "distance": 5000,
            "moving_time": 1800,
            "calories": 420,
        }
    ]
    result = hd.import_intervals_activities(activities)
    assert result["imported"] == 1
    result2 = hd.import_intervals_activities(activities)
    assert result2["imported"] == 1


def test_import_intervals_wellness(temp_health_db):
    rows = [{"id": "2026-06-15", "weight": 111.1}, {"id": "2026-06-16", "weight": 50.0}]
    result = hd.import_intervals_wellness(rows)
    assert result["imported"] == 1
    assert result["skipped"] == 1
    df = hd.load_measurements_df()
    intervals = df[df["source"] == "intervals"]
    assert len(intervals) == 1
    assert float(intervals.iloc[0]["weight_kg"]) == 111.1


def test_intervals_config_missing(monkeypatch):
    monkeypatch.delenv("INTERVALS_ICU_API_KEY", raising=False)
    monkeypatch.delenv("INTERVALS_ICU_ATHLETE_ID", raising=False)
    assert icu.intervals_config() is None


def test_intervals_config_normalizes_id(monkeypatch):
    monkeypatch.setenv("INTERVALS_ICU_API_KEY", "test-key")
    monkeypatch.setenv("INTERVALS_ICU_ATHLETE_ID", "i615695")
    cfg = icu.intervals_config()
    assert cfg == {"api_key": "test-key", "athlete_id": "i615695"}
    monkeypatch.setenv("INTERVALS_ICU_ATHLETE_ID", "615695")
    cfg2 = icu.intervals_config()
    assert cfg2 == {"api_key": "test-key", "athlete_id": "i615695"}
