"""Pull activities and wellness from Intervals.icu into health.db."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from health_db import get_connection, import_intervals_activities, import_intervals_wellness, init_db, set_import_meta

BASE_URL = "https://intervals.icu/api/v1"
DEFAULT_DAYS_BACK = 400


def _api_athlete_id(raw: str) -> str:
    """Intervals.icu accepts 0 (= account of the API key) or i-prefixed id."""
    athlete_id = raw.strip()
    if not athlete_id or athlete_id == "0":
        return "0"
    if athlete_id.lower().startswith("i"):
        return athlete_id
    return f"i{athlete_id}"


def intervals_config() -> dict[str, str] | None:
    api_key = os.environ.get("INTERVALS_ICU_API_KEY", "").strip()
    athlete_id = os.environ.get("INTERVALS_ICU_ATHLETE_ID", "").strip()
    if not api_key or not athlete_id:
        return None
    return {
        "api_key": api_key,
        "athlete_id": _api_athlete_id(athlete_id),
    }


def _date_range(days_back: int | None = None) -> tuple[str, str]:
    days = days_back
    if days is None:
        days = int(os.environ.get("INTERVALS_ICU_DAYS_BACK", DEFAULT_DAYS_BACK))
    newest = date.today()
    oldest = newest - timedelta(days=max(1, days))
    return oldest.isoformat(), newest.isoformat()


def _fetch_json(
    client: httpx.Client,
    athlete_id: str,
    resource: str,
    *,
    params: dict[str, str] | None = None,
) -> Any:
    url = f"{BASE_URL}/athlete/{athlete_id}/{resource}"
    response = client.get(url, params=params or {})
    response.raise_for_status()
    return response.json()


def fetch_activities(
    *,
    api_key: str,
    athlete_id: str,
    oldest: str,
    newest: str,
) -> list[dict[str, Any]]:
    with httpx.Client(
        auth=("API_KEY", api_key),
        timeout=60.0,
        headers={"Accept": "application/json"},
    ) as client:
        data = _fetch_json(
            client,
            athlete_id,
            "activities",
            params={"oldest": oldest, "newest": newest},
        )
    if not isinstance(data, list):
        raise ValueError("Unexpected Intervals.icu activities response")
    return data


def fetch_wellness(
    *,
    api_key: str,
    athlete_id: str,
    oldest: str,
    newest: str,
) -> list[dict[str, Any]]:
    with httpx.Client(
        auth=("API_KEY", api_key),
        timeout=60.0,
        headers={"Accept": "application/json"},
    ) as client:
        data = _fetch_json(
            client,
            athlete_id,
            "wellness",
            params={"oldest": oldest, "newest": newest},
        )
    if not isinstance(data, list):
        raise ValueError("Unexpected Intervals.icu wellness response")
    return data


def _last_sync_age_seconds() -> float | None:
    init_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT updated_at FROM import_meta WHERE key = 'intervals_sync'"
    ).fetchone()
    conn.close()
    if not row or not row[0]:
        return None
    try:
        updated = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
    except ValueError:
        return None
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - updated).total_seconds()


def should_sync_intervals(min_interval_sec: int = 3600) -> bool:
    age = _last_sync_age_seconds()
    return age is None or age >= min_interval_sec


def sync_intervals(*, days_back: int | None = None, force: bool = False) -> dict[str, Any]:
    """Download activities + wellness weight from Intervals.icu."""
    cfg = intervals_config()
    if cfg is None:
        return {"ok": False, "error": "INTERVALS_ICU_API_KEY or INTERVALS_ICU_ATHLETE_ID not set"}
    if not force and not should_sync_intervals():
        return {"ok": True, "skipped": True, "reason": "synced recently"}

    oldest, newest = _date_range(days_back)
    try:
        activities = fetch_activities(
            api_key=cfg["api_key"],
            athlete_id=cfg["athlete_id"],
            oldest=oldest,
            newest=newest,
        )
        wellness = fetch_wellness(
            api_key=cfg["api_key"],
            athlete_id=cfg["athlete_id"],
            oldest=oldest,
            newest=newest,
        )
    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "error": f"Intervals.icu HTTP {exc.response.status_code}",
            "range": {"oldest": oldest, "newest": newest},
        }
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "range": {"oldest": oldest, "newest": newest}}

    act_result = import_intervals_activities(activities)
    wellness_result = import_intervals_wellness(wellness)
    synced_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    set_import_meta(
        "intervals_sync",
        f"{oldest}..{newest} · activities={act_result['imported']} wellness={wellness_result['imported']}",
    )
    return {
        "ok": True,
        "forced": force,
        "range": {"oldest": oldest, "newest": newest},
        "activities": act_result,
        "wellness": wellness_result,
        "synced_at": synced_at,
    }


if __name__ == "__main__":
    import json
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
    print(json.dumps(sync_intervals(force=True), ensure_ascii=False, indent=2))
