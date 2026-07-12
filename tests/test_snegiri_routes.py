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
    assert len(r4.json()["items"]) >= 15


def test_snegiri_program_k_phase(client: TestClient) -> None:
    r = client.get("/api/snegiri/program", params={"track": "K", "day": 1, "unlocked_phase": 1})
    body = r.json()
    assert body["phaseName"] == "Углы без импульса"
    slugs = {e["slug"] for e in body["exercises"]}
    assert "hip_hinge" in slugs or "goblet_squat" in slugs


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
