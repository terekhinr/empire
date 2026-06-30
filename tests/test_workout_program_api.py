"""Tests for workout program API."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

import planning_api as api


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(api, "PLANNING_API_TOKEN", "test-token")
    api.init_db()
    api.init_health_db()
    return TestClient(api.app)


def test_program_session_today(client):
    r = client.get(
        "/api/planning/workouts/program/session",
        params={"on": "2026-06-24"},
        headers={"X-Planning-Token": "test-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["label"].startswith("Фаза 1")
    assert any(ex["exercise_key"] == "жим_штанги_лежа" for ex in data["exercises"])


def test_program_log_batch(client):
    r = client.post(
        "/api/planning/workouts/program/log-batch",
        headers={"X-Planning-Token": "test-token"},
        json={
            "logged_on": "2026-06-24",
            "entries": [
                {
                    "logged_on": "2026-06-24",
                    "exercise_key": "жим_штанги_лежа",
                    "weight_kg": 107.5,
                    "reps": 5,
                    "sets": 4,
                }
            ],
        },
    )
    assert r.status_code == 200
    assert r.json()["saved"] == 1
