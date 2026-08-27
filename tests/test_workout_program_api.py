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
        params={"on": "2026-06-24", "anchor": "2026-06-24", "start_day": "A"},
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


def test_outside_hall_summary_and_session(client):
    r = client.get(
        "/api/planning/workouts/program/summary",
        params={"program": "outside_hall", "anchor": "2026-07-20", "start_day": "A"},
        headers={"X-Planning-Token": "test-token"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["program_id"] == "outside_hall"
    assert data["title"] == "Работа вне зала"
    assert data["calendar_days"] == 9
    assert data["schedule_anchor"] == "2026-07-20"
    assert len(data["programs"]) >= 2

    s = client.get(
        "/api/planning/workouts/program/session",
        params={
            "on": "2026-07-22",
            "program": "outside_hall",
            "anchor": "2026-07-20",
            "start_day": "A",
        },
        headers={"X-Planning-Token": "test-token"},
    )
    assert s.status_code == 200
    body = s.json()
    assert body["day"] == "B"
    assert any(ex["exercise_key"] == "бег_по_резиновому_стадиону_400м" for ex in body["exercises"])
    plank = next(ex for ex in body["exercises"] if ex["exercise_key"] == "боковая_планка_макгилла")
    assert plank["is_time_hold"] is True


def test_outside_hall_log_batch_isolated(client):
    r = client.post(
        "/api/planning/workouts/program/log-batch",
        headers={"X-Planning-Token": "test-token"},
        json={
            "logged_on": "2026-08-05",
            "program_id": "outside_hall",
            "replace_program": True,
            "entries": [
                {
                    "logged_on": "2026-08-05",
                    "exercise_key": "классические_отжимания_от_пола_без_веса",
                    "weight_kg": 0,
                    "reps": 15,
                    "sets": 1,
                    "note": "подход 1/2",
                }
            ],
        },
    )
    assert r.status_code == 200
    assert r.json()["saved"] == 1
    assert r.json()["program_id"] == "outside_hall"
    logs = client.get(
        "/api/planning/workouts",
        params={"logged_on": "2026-08-05"},
        headers={"X-Planning-Token": "test-token"},
    ).json()["workouts"]
    assert any((w.get("note") or "").startswith("внезала подход") for w in logs)
