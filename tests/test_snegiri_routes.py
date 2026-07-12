"""Snegiri API routes."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    import importlib

    import web_app

    importlib.reload(web_app)
    return TestClient(web_app.app)


def test_snegiri_health(client: TestClient) -> None:
    r = client.get("/api/snegiri/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_snegiri_session_and_program(client: TestClient) -> None:
    r = client.post("/api/snegiri/session")
    assert r.status_code == 200
    sid = r.json()["id"]

    r2 = client.get(f"/api/snegiri/session/{sid}")
    assert r2.status_code == 200

    r3 = client.get("/api/snegiri/program", params={"track": "S", "day": 1})
    assert r3.status_code == 200
    body = r3.json()
    assert body["day"] == 1
    assert body["phase"] == 1
    assert len(body["exercises"]) >= 2

    r4 = client.get("/api/snegiri/exercises")
    assert r4.status_code == 200
    assert len(r4.json()["items"]) >= 20


def test_snegiri_program_k_phase(client: TestClient) -> None:
    r = client.get("/api/snegiri/program", params={"track": "K", "day": 1, "unlocked_phase": 1})
    body = r.json()
    assert body["phaseName"] == "Наклон"
    slugs = {e["slug"] for e in body["exercises"]}
    assert "hip_hinge" in slugs


def test_snegiri_program_k_swing_phase(client: TestClient) -> None:
    r = client.get("/api/snegiri/program", params={"track": "K", "day": 52, "unlocked_phase": 4})
    body = r.json()
    assert body["phaseName"] == "Свинг двуручный"
    assert any(e["slug"] == "swing" for e in body["exercises"])


def test_snegiri_program_k_hand_switch_phase(client: TestClient) -> None:
    r = client.get("/api/snegiri/program", params={"track": "K", "day": 86, "unlocked_phase": 6})
    body = r.json()
    assert body["phaseName"] == "Смена рук"
    assert any(e["slug"] == "hand_switch" for e in body["exercises"])


def test_snegiri_program_k_track_length(client: TestClient) -> None:
    from snegiri_kb.program_data import TRACK_DAYS, build_day

    assert TRACK_DAYS["K"] == 187
    day = build_day(187, track="K", unlocked_phase=11)
    assert day["phase"] == 11
    assert any(e["slug"] == "complex" for e in day["exercises"])


def test_snegiri_exercise_refs(client: TestClient) -> None:
    r = client.get("/api/snegiri/exercise-refs")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 25
    slugs = {i["slug"] for i in items}
    assert "hand_switch" in slugs
    assert "curl_up" in slugs


def test_snegiri_analyze_short_video_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/snegiri/analyze",
        data={"exercise": "side_plank"},
        files={"video": ("t.webm", io.BytesIO(b"x"), "video/webm")},
    )
    assert r.status_code == 400


def test_snegiri_analyze_accepts_video(client: TestClient) -> None:
    blob = b"0" * 2048
    r = client.post(
        "/api/snegiri/analyze",
        data={"exercise": "side_plank"},
        files={"video": ("t.webm", io.BytesIO(blob), "video/webm")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "score" in data
    assert data["exercise"] == "side_plank"
