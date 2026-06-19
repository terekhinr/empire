"""Parse Health Connect webhook JSON (HC Webhook app) into health.db."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from health_db import get_connection, init_db, sanitize_weight, set_import_meta


def _parse_instant(value: str | None) -> datetime | None:
    if not value:
        return None
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.to_pydatetime()


def _day_key(value: str | None) -> str | None:
    ts = _parse_instant(value)
    if ts is None:
        return None
    return ts.date().isoformat()


def ingest_weight_records(records: list[dict[str, Any]]) -> dict[str, int]:
    init_db()
    conn = get_connection()
    imported = skipped = 0
    for row in records:
        kg = sanitize_weight(row.get("kilograms"))
        if kg is None:
            skipped += 1
            continue
        ts = _parse_instant(row.get("time"))
        if ts is None:
            skipped += 1
            continue
        measured_at = ts.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
        try:
            conn.execute(
                """
                INSERT INTO body_scale (measured_at, weight_kg, source_file)
                VALUES (?, ?, 'health_connect')
                ON CONFLICT(measured_at) DO UPDATE SET
                    weight_kg=excluded.weight_kg,
                    source_file=excluded.source_file
                """,
                (measured_at, kg),
            )
            day = ts.date().isoformat()
            existing = conn.execute(
                "SELECT id FROM measurements WHERE measured_on = ? AND source = 'health_connect' LIMIT 1",
                (day,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE measurements SET weight_kg = ? WHERE id = ?",
                    (kg, existing["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO measurements (measured_on, weight_kg, source) VALUES (?, ?, 'health_connect')",
                    (day, kg),
                )
            imported += 1
        except Exception:
            skipped += 1
    conn.commit()
    conn.close()
    return {"imported": imported, "skipped": skipped}


def ingest_body_fat_records(records: list[dict[str, Any]]) -> dict[str, int]:
    init_db()
    conn = get_connection()
    imported = skipped = 0
    for row in records:
        pct = row.get("percentage")
        if pct is None:
            skipped += 1
            continue
        try:
            fat_pct = float(pct)
        except (TypeError, ValueError):
            skipped += 1
            continue
        if fat_pct <= 0:
            skipped += 1
            continue
        ts = _parse_instant(row.get("time"))
        if ts is None:
            skipped += 1
            continue
        measured_at = ts.astimezone(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
        try:
            conn.execute(
                """
                INSERT INTO body_scale (measured_at, fat_pct, source_file)
                VALUES (?, ?, 'health_connect')
                ON CONFLICT(measured_at) DO UPDATE SET
                    fat_pct=excluded.fat_pct,
                    source_file=excluded.source_file
                """,
                (measured_at, fat_pct),
            )
            imported += 1
        except Exception:
            skipped += 1
    conn.commit()
    conn.close()
    return {"imported": imported, "skipped": skipped}


def ingest_nutrition_records(records: list[dict[str, Any]]) -> dict[str, int]:
    daily: dict[str, dict[str, float]] = defaultdict(
        lambda: {"calories": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0}
    )
    skipped = 0
    for row in records:
        day = _day_key(row.get("start_time") or row.get("end_time"))
        if not day:
            skipped += 1
            continue
        bucket = daily[day]
        for src, dst in (
            ("calories", "calories"),
            ("protein_grams", "protein_g"),
            ("fat_grams", "fat_g"),
            ("carbs_grams", "carbs_g"),
        ):
            val = row.get(src)
            if val is None:
                continue
            try:
                bucket[dst] += float(val)
            except (TypeError, ValueError):
                continue

    init_db()
    conn = get_connection()
    imported = 0
    for day, totals in daily.items():
        if not any(totals.values()):
            continue
        conn.execute(
            """
            INSERT INTO food_daily (day, calories, protein_g, fat_g, carbs_g, source_file)
            VALUES (?, ?, ?, ?, ?, 'health_connect')
            ON CONFLICT(day) DO UPDATE SET
                calories=excluded.calories,
                protein_g=excluded.protein_g,
                fat_g=excluded.fat_g,
                carbs_g=excluded.carbs_g,
                source_file=excluded.source_file
            """,
            (day, totals["calories"], totals["protein_g"], totals["fat_g"], totals["carbs_g"]),
        )
        imported += 1
    conn.commit()
    conn.close()
    return {"imported": imported, "skipped": skipped}


def ingest_health_connect_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Import supported HC Webhook arrays into health.db."""
    results: dict[str, Any] = {"ok": True, "types": []}

    if weight := payload.get("weight"):
        if isinstance(weight, list) and weight:
            results["weight"] = ingest_weight_records(weight)
            results["types"].append("weight")

    if body_fat := payload.get("body_fat"):
        if isinstance(body_fat, list) and body_fat:
            results["body_fat"] = ingest_body_fat_records(body_fat)
            results["types"].append("body_fat")

    if nutrition := payload.get("nutrition"):
        if isinstance(nutrition, list) and nutrition:
            results["nutrition"] = ingest_nutrition_records(nutrition)
            results["types"].append("nutrition")

    if not results["types"]:
        results["ok"] = True
        results["message"] = "no supported records in payload"
    else:
        set_import_meta("health_connect", ", ".join(results["types"]))

    return results
