"""Tests for empire-workout-program/v1 and upload API."""

from __future__ import annotations

from pathlib import Path

import json
import pytest
from fastapi.testclient import TestClient

import health_workout_program as hwp
import planning_api as api
from workout_program_v1 import loads, slugify_id


SAMPLE = """
{
  "schema": "empire-workout-program/v1",
  "id": "test_cycle",
  "title": "Тест",
  "short": "Тест",
  "weekdays": ["mon", "fri"],
  "rolling_sessions": 4,
  "phases": [
    {
      "id": 1,
      "title": "База",
      "days": [
        {
          "id": "A",
          "title": "Сила",
          "exercises": [
            {"key": "custom_row", "name": "Тяга своя", "sets": 3, "reps": [8, 10], "weight_kg": 40}
          ]
        },
        {
          "id": "B",
          "title": "Планка",
          "exercises": [
            {"key": "классическая_планка_на_предплечьях", "sets": 2, "hold_sec": 40, "is_time_hold": true}
          ]
        }
      ]
    }
  ]
}
"""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import health_db as hd

    db_dir = tmp_path / "health"
    db_dir.mkdir()
    monkeypatch.setattr(hd, "HEALTH_DIR", db_dir)
    monkeypatch.setattr(hd, "HEALTH_DB_PATH", db_dir / "health.db")
    monkeypatch.setattr(api, "PLANNING_API_TOKEN", "test-token")
    monkeypatch.setattr(hwp, "USER_PROGRAMS_DIR", tmp_path / "programs")
    hwp.USER_PROGRAMS_DIR.mkdir(parents=True)
    hwp.invalidate_program_cache()
    api.init_db()
    api.init_health_db()
    return TestClient(api.app)


def auth():
    return {"X-Planning-Token": "test-token"}


def test_loads_json_and_weekdays():
    spec = loads(SAMPLE, filename="test_cycle.json")
    assert spec["id"] == "test_cycle"
    assert spec["weekdays"] == [0, 4]
    assert spec["phases"][0]["days"][0]["exercises"][0]["reps_min"] == 8
    assert spec["phases"][0]["days"][1]["exercises"][0]["is_time_hold"] is True


def test_slugify_and_reserved_upload(client):
    assert slugify_id("Gym 2026!!") == "gym_2026"
    assert slugify_id("full_body_3day") == "full_body_3day"
    reserved = {
        "schema": "empire-workout-program/v1",
        "id": "gym_2026",
        "title": "Nope",
        "phases": [
            {
                "id": 1,
                "title": "X",
                "days": [{"id": "A", "title": "A", "exercises": [{"key": "отдых", "sets": 0}]}],
            }
        ],
    }
    r = client.post(
        "/api/planning/workouts/program/upload",
        headers=auth(),
        files={"file": ("gym.json", json.dumps(reserved).encode("utf-8"), "application/json")},
    )
    assert r.status_code == 400
    assert "reserved" in r.text


def test_upload_json_registers_custom_exercise(client):
    r = client.post(
        "/api/planning/workouts/program/upload",
        headers=auth(),
        files={"file": ("test_cycle.json", SAMPLE.encode("utf-8"), "application/json")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["program"]["id"] == "test_cycle"
    ids = {p["id"] for p in body["programs"]}
    assert "test_cycle" in ids
    assert "gym_2026" in ids
    exercises = client.get("/api/planning/body/exercises", headers=auth()).json()["exercises"]
    assert exercises["custom_row"] == "Тяга своя"


def test_upload_session_and_log(client):
    client.post(
        "/api/planning/workouts/program/upload",
        headers=auth(),
        files={"file": ("test_cycle.json", SAMPLE.encode("utf-8"), "application/json")},
    )
    s = client.get(
        "/api/planning/workouts/program/session",
        params={"on": "2026-09-07", "program": "test_cycle", "anchor": "2026-09-07", "start_day": "A"},
        headers=auth(),
    )
    assert s.status_code == 200, s.text
    assert s.json()["day"] == "A"
    keys = [ex["exercise_key"] for ex in s.json()["exercises"]]
    assert "custom_row" in keys
    log = client.post(
        "/api/planning/workouts/program/log-batch",
        headers=auth(),
        json={
            "logged_on": "2026-09-07",
            "program_id": "test_cycle",
            "replace_program": True,
            "entries": [
                {
                    "logged_on": "2026-09-07",
                    "exercise_key": "custom_row",
                    "weight_kg": 42.5,
                    "reps": 9,
                    "sets": 1,
                    "note": "подход 1/3",
                }
            ],
        },
    )
    assert log.status_code == 200
    assert log.json()["saved"] == 1


def test_cannot_delete_builtin(client):
    r = client.delete("/api/planning/workouts/program/gym_2026", headers=auth())
    assert r.status_code == 404


def test_delete_user_program(client):
    client.post(
        "/api/planning/workouts/program/upload",
        headers=auth(),
        files={"file": ("test_cycle.json", SAMPLE.encode("utf-8"), "application/json")},
    )
    r = client.delete("/api/planning/workouts/program/test_cycle", headers=auth())
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["programs"]}
    assert "test_cycle" not in ids


def test_example_file_parses():
    path = Path("/root/projects/empire/docs/health/examples/full_body_3day.json")
    spec = loads(path.read_text(encoding="utf-8"), filename=path.name)
    assert spec["id"] == "full_body_3day"
    assert len(spec["phases"][0]["days"]) == 3
