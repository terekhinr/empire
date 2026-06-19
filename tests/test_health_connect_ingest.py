"""Tests for Health Connect webhook ingest."""

from __future__ import annotations

import health_connect_ingest as hci
import health_db as hd


def test_ingest_nutrition_and_weight(temp_health_db):
    payload = {
        "timestamp": "2026-06-16T12:00:00Z",
        "app_version": "1.0.0",
        "nutrition": [
            {
                "start_time": "2026-06-16T08:00:00Z",
                "end_time": "2026-06-16T08:30:00Z",
                "calories": 500,
                "protein_grams": 30,
                "fat_grams": 15,
                "carbs_grams": 40,
                "name": "Breakfast",
            },
            {
                "start_time": "2026-06-16T13:00:00Z",
                "end_time": "2026-06-16T13:30:00Z",
                "calories": 700,
                "protein_grams": 40,
                "fat_grams": 20,
                "carbs_grams": 60,
            },
        ],
        "weight": [
            {"kilograms": 111.1, "time": "2026-06-16T06:30:00Z"},
        ],
    }
    result = hci.ingest_health_connect_payload(payload)
    assert result["ok"] is True
    assert "nutrition" in result["types"]
    assert "weight" in result["types"]

    food = hd.load_food_daily()
    assert not food.empty
    row = food.iloc[-1]
    assert float(row["calories"]) == 1200
    assert float(row["protein_g"]) == 70

    scale = hd.load_body_scale_daily()
    assert not scale.empty

    measurements = hd.load_measurements_df()
    hc = measurements[measurements["source"] == "health_connect"]
    assert len(hc) == 1
