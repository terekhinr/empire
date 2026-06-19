"""SQLite storage for health dashboard: measurements, strength, CSV imports."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
HEALTH_DIR = BASE_DIR / "data" / "health"
HEALTH_DB_PATH = HEALTH_DIR / "health.db"
SEED_PATH = HEALTH_DIR / "measurements_seed.json"
BODY_DATA_DIR = BASE_DIR / "data" / "pension" / "body"

DEFAULT_HEIGHT_CM = 186.0
WEIGHT_MIN_KG = 90.0
WEIGHT_MAX_KG = 120.0

STRENGTH_EXERCISES = {
    "bench_press": "Жим лёжа",
    "leg_press": "Жим ногами",
    "row": "Тяга в наклоне",
    "biceps": "Бицепс",
    "triceps": "Трицепс",
}


def get_connection() -> sqlite3.Connection:
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(HEALTH_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            measured_on TEXT NOT NULL,
            weight_kg REAL,
            waist_cm REAL,
            biceps_r_cm REAL,
            biceps_l_cm REAL,
            legs_cm REAL,
            note TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_measurements_date ON measurements(measured_on);

        CREATE TABLE IF NOT EXISTS strength_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_on TEXT NOT NULL,
            exercise_key TEXT NOT NULL,
            weight_kg REAL NOT NULL,
            reps INTEGER NOT NULL,
            sets INTEGER NOT NULL DEFAULT 1,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_strength_date ON strength_logs(logged_on);
        CREATE INDEX IF NOT EXISTS idx_strength_exercise ON strength_logs(exercise_key);

        CREATE TABLE IF NOT EXISTS body_scale (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            measured_at TEXT NOT NULL UNIQUE,
            weight_kg REAL,
            fat_pct REAL,
            muscle_pct REAL,
            visceral REAL,
            metabolism REAL,
            source_file TEXT
        );

        CREATE TABLE IF NOT EXISTS food_daily (
            day TEXT PRIMARY KEY,
            calories REAL,
            protein_g REAL,
            fat_g REAL,
            carbs_g REAL,
            source_file TEXT
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_on TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            name TEXT,
            distance_km REAL,
            calories REAL,
            duration_min REAL,
            source_file TEXT,
            UNIQUE(activity_on, activity_type, name, distance_km, duration_min)
        );

        CREATE TABLE IF NOT EXISTS import_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    _ensure_activities_external_id(conn)
    conn.commit()
    conn.close()


def _ensure_activities_external_id(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(activities)").fetchall()}
    if "external_id" not in cols:
        conn.execute("ALTER TABLE activities ADD COLUMN external_id TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_external_id ON activities(external_id)"
    )


INTERVALS_ACTIVITY_TYPE_RU = {
    "Run": "Бег",
    "VirtualRun": "Бег",
    "TrailRun": "Бег",
    "Treadmill": "Бег",
    "Ride": "Велосипед",
    "VirtualRide": "Велосипед",
    "Swim": "Плавание",
    "OpenWaterSwim": "Плавание",
    "PoolSwim": "Плавание",
    "WeightTraining": "Силовая",
    "Strength": "Силовая",
    "Walking": "Ходьба",
    "Hike": "Поход",
    "Rowing": "Гребля",
    "Other": "Другое",
}


def _intervals_activity_type_ru(activity_type: str | None) -> str:
    if not activity_type:
        return "Другое"
    return INTERVALS_ACTIVITY_TYPE_RU.get(activity_type, activity_type)


def _intervals_distance_km(activity: dict[str, Any]) -> float | None:
    distance = activity.get("distance")
    if distance is None:
        return None
    try:
        km = float(distance) / 1000.0
    except (TypeError, ValueError):
        return None
    if km <= 0:
        return None
    return km


def _intervals_duration_min(activity: dict[str, Any]) -> float | None:
    for key in ("moving_time", "elapsed_time"):
        seconds = activity.get(key)
        if seconds is None:
            continue
        try:
            sec = float(seconds)
        except (TypeError, ValueError):
            continue
        if sec > 0:
            return sec / 60.0
    return None


def _intervals_calories(activity: dict[str, Any]) -> float | None:
    for key in ("calories", "icu_calories"):
        value = activity.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _intervals_activity_on(activity: dict[str, Any]) -> str | None:
    for key in ("start_date_local", "start_date"):
        raw = activity.get(key)
        if not raw:
            continue
        ts = pd.to_datetime(raw, errors="coerce")
        if pd.isna(ts):
            continue
        return ts.to_pydatetime().replace(tzinfo=None).isoformat(sep=" ")
    return None


def import_intervals_activities(activities: list[dict[str, Any]]) -> dict[str, int]:
    init_db()
    conn = get_connection()
    imported = skipped = 0
    for activity in activities:
        activity_id = activity.get("id")
        if activity_id is None:
            skipped += 1
            continue
        external_id = f"intervals:{activity_id}"
        activity_on = _intervals_activity_on(activity)
        if not activity_on:
            skipped += 1
            continue
        activity_type = _intervals_activity_type_ru(str(activity.get("type") or ""))
        name = str(activity.get("name") or "").strip() or None
        distance_km = _intervals_distance_km(activity)
        calories = _intervals_calories(activity)
        duration_min = _intervals_duration_min(activity)
        try:
            conn.execute(
                """
                INSERT INTO activities (
                    activity_on, activity_type, name, distance_km, calories, duration_min,
                    source_file, external_id
                ) VALUES (?, ?, ?, ?, ?, ?, 'intervals.icu', ?)
                ON CONFLICT(external_id) DO UPDATE SET
                    activity_on=excluded.activity_on,
                    activity_type=excluded.activity_type,
                    name=excluded.name,
                    distance_km=excluded.distance_km,
                    calories=excluded.calories,
                    duration_min=excluded.duration_min,
                    source_file=excluded.source_file
                """,
                (
                    activity_on,
                    activity_type,
                    name,
                    distance_km,
                    calories,
                    duration_min,
                    external_id,
                ),
            )
            imported += 1
        except sqlite3.Error:
            skipped += 1
    conn.commit()
    conn.close()
    return {"imported": imported, "skipped": skipped}


def import_intervals_wellness(rows: list[dict[str, Any]]) -> dict[str, int]:
    init_db()
    conn = get_connection()
    imported = skipped = 0
    for row in rows:
        day = str(row.get("id") or "").strip()
        weight = row.get("weight")
        if not day or weight is None:
            skipped += 1
            continue
        weight_kg = sanitize_weight(float(weight))
        if weight_kg is None:
            skipped += 1
            continue
        existing = conn.execute(
            "SELECT id FROM measurements WHERE measured_on = ? AND source = 'intervals' LIMIT 1",
            (day,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE measurements SET weight_kg = ? WHERE id = ?",
                (weight_kg, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO measurements (measured_on, weight_kg, source)
                VALUES (?, ?, 'intervals')
                """,
                (day, weight_kg),
            )
        imported += 1
    conn.commit()
    conn.close()
    return {"imported": imported, "skipped": skipped}


def set_import_meta(key: str, value: str) -> None:
    init_db()
    conn = get_connection()
    conn.execute(
        "INSERT INTO import_meta(key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value),
    )
    conn.commit()
    conn.close()


def seed_measurements_if_empty() -> int:
    init_db()
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    if n > 0:
        conn.close()
        return 0
    if not SEED_PATH.exists():
        conn.close()
        return 0
    rows = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    inserted = 0
    for row in rows:
        conn.execute(
            """
            INSERT INTO measurements (
                measured_on, weight_kg, waist_cm, biceps_r_cm, biceps_l_cm, legs_cm, note, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'seed')
            """,
            (
                row["date"],
                row.get("weight_kg"),
                row.get("waist_cm"),
                row.get("biceps_r_cm"),
                row.get("biceps_l_cm"),
                row.get("legs_cm"),
                row.get("note"),
            ),
        )
        inserted += 1
    conn.commit()
    conn.close()
    return inserted


def add_measurement(
    measured_on: str,
    *,
    weight_kg: float | None = None,
    waist_cm: float | None = None,
    biceps_r_cm: float | None = None,
    biceps_l_cm: float | None = None,
    legs_cm: float | None = None,
    note: str | None = None,
    source: str = "manual",
) -> int:
    init_db()
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO measurements (
            measured_on, weight_kg, waist_cm, biceps_r_cm, biceps_l_cm, legs_cm, note, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (measured_on, weight_kg, waist_cm, biceps_r_cm, biceps_l_cm, legs_cm, note, source),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return int(row_id)


def add_strength_log(
    logged_on: str,
    exercise_key: str,
    weight_kg: float,
    reps: int,
    sets: int = 1,
    note: str | None = None,
) -> int:
    if exercise_key not in STRENGTH_EXERCISES:
        raise ValueError(f"Unknown exercise: {exercise_key}")
    init_db()
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO strength_logs (logged_on, exercise_key, weight_kg, reps, sets, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (logged_on, exercise_key, weight_kg, reps, sets, note),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return int(row_id)


def load_measurements_df() -> pd.DataFrame:
    init_db()
    seed_measurements_if_empty()
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM measurements ORDER BY measured_on, id",
        conn,
    )
    conn.close()
    if df.empty:
        return df
    df["measured_on"] = pd.to_datetime(df["measured_on"])
    return df


def load_strength_df() -> pd.DataFrame:
    init_db()
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM strength_logs ORDER BY logged_on, id",
        conn,
    )
    conn.close()
    if df.empty:
        return df
    df["logged_on"] = pd.to_datetime(df["logged_on"])
    df["exercise_label"] = df["exercise_key"].map(STRENGTH_EXERCISES)
    return df


def measurements_daily_summary(df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = load_measurements_df()
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    work["weight_kg"] = work["weight_kg"].apply(sanitize_weight)
    agg = {
        "weight_kg": "mean",
        "waist_cm": "mean",
        "biceps_r_cm": "mean",
        "biceps_l_cm": "mean",
        "legs_cm": "mean",
    }
    out = work.groupby(work["measured_on"].dt.date).agg(agg).reset_index()
    out.rename(columns={"measured_on": "date"}, inplace=True)
    out["date"] = pd.to_datetime(out["date"])
    out["biceps_avg_cm"] = (out["biceps_r_cm"] + out["biceps_l_cm"]) / 2
    out["bmi"] = out["weight_kg"] / ((DEFAULT_HEIGHT_CM / 100) ** 2)
    out["whtr"] = out["waist_cm"] / DEFAULT_HEIGHT_CM
    return out


def sanitize_weight(value: float | None) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    v = float(value)
    if v < WEIGHT_MIN_KG or v > WEIGHT_MAX_KG:
        return None
    return v


def smooth_series(series: pd.Series, window: int = 5) -> pd.Series:
    if series.empty:
        return series
    w = max(3, window)
    return series.rolling(window=w, min_periods=1, center=True).mean()


def prepare_chart_frame(
    df: pd.DataFrame,
    *,
    date_col: str = "date",
    smooth_cols: list[str] | None = None,
    smooth_window: int = 5,
    weight_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Filter weight outliers and add smoothed columns for charts."""
    if df.empty:
        return df
    out = df.sort_values(date_col).copy()
    weight_cols = weight_cols or []
    for col in weight_cols:
        if col in out.columns:
            out[col] = out[col].apply(sanitize_weight)
    smooth_cols = smooth_cols or []
    for col in smooth_cols:
        if col not in out.columns:
            continue
        raw = out[col].copy()
        out[f"{col}_raw"] = raw
        out[f"{col}_smooth"] = smooth_series(raw, window=smooth_window)
    return out


def _parse_ru_number(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if s in ("", "--", "null", "None"):
        return None
    if re.match(r"^\d{1,3}(,\d{3})+$", s):
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_duration_minutes(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if s in ("", "--"):
        return None
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h, m, sec = parts
            sec = float(sec.replace(",", "."))
            return int(h) * 60 + int(m) + sec / 60
        if len(parts) == 2:
            m, sec = parts
            sec = float(sec.replace(",", "."))
            return int(m) + sec / 60
    except ValueError:
        return None
    return None


def import_body_scale_csv(path: Path | None = None) -> dict[str, int]:
    init_db()
    if path is None:
        files = sorted(BODY_DATA_DIR.glob("BODY_*.csv"))
        path = files[0] if files else None
    if path is None or not path.exists():
        return {"imported": 0, "skipped": 0}

    raw = pd.read_csv(path)
    raw["time"] = pd.to_datetime(raw["time"], utc=True, errors="coerce").dt.tz_convert(None)
    for col in ("weight", "fatRate", "muscleRate", "visceralFat", "metabolism"):
        raw[col] = pd.to_numeric(raw[col], errors="coerce")
    raw = raw[(raw["weight"] >= WEIGHT_MIN_KG) & (raw["weight"] <= WEIGHT_MAX_KG)]

    conn = get_connection()
    imported = skipped = 0
    for _, row in raw.iterrows():
        ts = row["time"]
        if pd.isna(ts):
            skipped += 1
            continue
        measured_at = ts.isoformat(sep=" ")
        try:
            conn.execute(
                """
                INSERT INTO body_scale (
                    measured_at, weight_kg, fat_pct, muscle_pct, visceral, metabolism, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(measured_at) DO UPDATE SET
                    weight_kg=excluded.weight_kg,
                    fat_pct=excluded.fat_pct,
                    muscle_pct=excluded.muscle_pct,
                    visceral=excluded.visceral,
                    metabolism=excluded.metabolism,
                    source_file=excluded.source_file
                """,
                (
                    measured_at,
                    row.get("weight"),
                    row.get("fatRate") if row.get("fatRate", 0) > 0 else None,
                    row.get("muscleRate") if row.get("muscleRate", 0) > 0 else None,
                    row.get("visceralFat") if row.get("visceralFat", 0) > 0 else None,
                    row.get("metabolism") if row.get("metabolism", 0) > 0 else None,
                    path.name,
                ),
            )
            imported += 1
        except sqlite3.Error:
            skipped += 1
    conn.execute(
        "INSERT INTO import_meta(key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        ("body_scale", path.name),
    )
    conn.commit()
    conn.close()
    return {"imported": imported, "skipped": skipped}


def import_food_csv(path: Path | None = None) -> dict[str, int]:
    init_db()
    path = path or (BODY_DATA_DIR / "food.csv")
    if not path.exists():
        return {"imported": 0, "skipped": 0}

    food = pd.read_csv(path)
    food["date"] = pd.to_datetime(food["date"], errors="coerce").dt.date.astype(str)
    for col in ("calories", "protein", "fat", "carbs"):
        food[col] = pd.to_numeric(food[col], errors="coerce").fillna(0)
    daily = food.groupby("date", as_index=False).agg(
        calories=("calories", "sum"),
        protein_g=("protein", "sum"),
        fat_g=("fat", "sum"),
        carbs_g=("carbs", "sum"),
    )

    conn = get_connection()
    imported = 0
    for _, row in daily.iterrows():
        conn.execute(
            """
            INSERT INTO food_daily (day, calories, protein_g, fat_g, carbs_g, source_file)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
                calories=excluded.calories,
                protein_g=excluded.protein_g,
                fat_g=excluded.fat_g,
                carbs_g=excluded.carbs_g,
                source_file=excluded.source_file
            """,
            (row["date"], row["calories"], row["protein_g"], row["fat_g"], row["carbs_g"], path.name),
        )
        imported += 1
    conn.execute(
        "INSERT INTO import_meta(key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        ("food_daily", path.name),
    )
    conn.commit()
    conn.close()
    return {"imported": imported}


def import_activities_csv(path: Path | None = None) -> dict[str, int]:
    init_db()
    if path is None:
        candidates = list(BODY_DATA_DIR.glob("Activities*.csv"))
        path = candidates[0] if candidates else None
    if path is None or not path.exists():
        return {"imported": 0, "skipped": 0}

    act = pd.read_csv(path)
    conn = get_connection()
    imported = skipped = 0
    for _, row in act.iterrows():
        activity_on = pd.to_datetime(row.get("Дата"), errors="coerce")
        if pd.isna(activity_on):
            skipped += 1
            continue
        activity_type = str(row.get("Тип занятия", "")).strip()
        name = str(row.get("Название", "")).strip()
        distance = _parse_ru_number(row.get("Расстояние"))
        if activity_type.startswith("Плав") and distance and distance > 500:
            distance = distance / 1000.0
        calories = _parse_ru_number(row.get("Калории"))
        duration = _parse_duration_minutes(row.get("Время"))
        try:
            conn.execute(
                """
                INSERT INTO activities (
                    activity_on, activity_type, name, distance_km, calories, duration_min, source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(activity_on, activity_type, name, distance_km, duration_min) DO NOTHING
                """,
                (
                    activity_on.isoformat(sep=" "),
                    activity_type,
                    name,
                    distance,
                    calories,
                    duration,
                    path.name,
                ),
            )
            imported += 1
        except sqlite3.Error:
            skipped += 1
    conn.execute(
        "INSERT INTO import_meta(key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        ("activities", path.name),
    )
    conn.commit()
    conn.close()
    return {"imported": imported, "skipped": skipped}


def sync_all_csv() -> dict[str, Any]:
    return {
        "body_scale": import_body_scale_csv(),
        "food": import_food_csv(),
        "activities": import_activities_csv(),
        "seeded": seed_measurements_if_empty(),
    }


def _csv_source_paths() -> dict[str, Path | None]:
    body_files = sorted(BODY_DATA_DIR.glob("BODY_*.csv"))
    act_files = list(BODY_DATA_DIR.glob("Activities*.csv"))
    return {
        "body_scale": body_files[0] if body_files else None,
        "food": BODY_DATA_DIR / "food.csv" if (BODY_DATA_DIR / "food.csv").exists() else None,
        "activities": act_files[0] if act_files else None,
    }


def _path_signature(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    st = path.stat()
    return f"{st.st_size}:{int(st.st_mtime)}"


def _load_file_signatures() -> dict[str, str]:
    init_db()
    conn = get_connection()
    row = conn.execute("SELECT value FROM import_meta WHERE key='file_signatures'").fetchone()
    conn.close()
    if not row or not row[0]:
        return {}
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return {}


def _save_file_signatures(sigs: dict[str, str]) -> None:
    init_db()
    conn = get_connection()
    conn.execute(
        "INSERT INTO import_meta(key, value, updated_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        ("file_signatures", json.dumps(sigs, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def sync_csv_if_changed(force: bool = False) -> dict[str, Any] | None:
    """Re-import CSV when source files changed (mtime/size). Returns result or None."""
    paths = _csv_source_paths()
    current = {k: _path_signature(p) for k, p in paths.items()}
    if not any(current.values()):
        return None
    prev = _load_file_signatures()
    if not force and prev == current:
        return None
    result = sync_all_csv()
    _save_file_signatures(current)
    result["changed"] = [k for k in current if prev.get(k) != current.get(k)]
    return result


def load_body_scale_daily() -> pd.DataFrame:
    init_db()
    conn = get_connection()
    df = pd.read_sql_query(
        f"""
        SELECT date(measured_at) AS date,
               AVG(weight_kg) AS scale_weight_kg,
               AVG(fat_pct) AS fat_pct,
               AVG(muscle_pct) AS muscle_pct,
               AVG(visceral) AS visceral
        FROM body_scale
        WHERE weight_kg IS NULL
           OR (weight_kg >= {WEIGHT_MIN_KG} AND weight_kg <= {WEIGHT_MAX_KG})
        GROUP BY date(measured_at)
        ORDER BY date
        """,
        conn,
    )
    conn.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["scale_weight_kg"] = df["scale_weight_kg"].apply(sanitize_weight)
    return df


def load_food_daily() -> pd.DataFrame:
    init_db()
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM food_daily ORDER BY day", conn)
    conn.close()
    if not df.empty:
        df["day"] = pd.to_datetime(df["day"])
    return df


def load_activities_monthly() -> pd.DataFrame:
    init_db()
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT strftime('%Y-%m', activity_on) AS month,
               activity_type,
               SUM(distance_km) AS distance_km,
               SUM(calories) AS calories,
               SUM(duration_min) AS duration_min,
               COUNT(*) AS sessions
        FROM activities
        GROUP BY month, activity_type
        ORDER BY month
        """,
        conn,
    )
    conn.close()
    return df


def load_import_meta() -> dict[str, str]:
    init_db()
    conn = get_connection()
    rows = conn.execute("SELECT key, value, updated_at FROM import_meta").fetchall()
    conn.close()
    return {r["key"]: f"{r['value']} · {r['updated_at']}" for r in rows}


def latest_measurement_summary() -> dict[str, Any]:
    daily = measurements_daily_summary()
    if daily.empty:
        return {}
    last = daily.iloc[-1]
    first = daily.iloc[0]
    return {
        "date": last["date"].date().isoformat(),
        "weight_kg": round(float(last["weight_kg"]), 1) if pd.notna(last["weight_kg"]) else None,
        "waist_cm": round(float(last["waist_cm"]), 1) if pd.notna(last["waist_cm"]) else None,
        "biceps_avg_cm": round(float(last["biceps_avg_cm"]), 1) if pd.notna(last["biceps_avg_cm"]) else None,
        "legs_cm": round(float(last["legs_cm"]), 1) if pd.notna(last["legs_cm"]) else None,
        "bmi": round(float(last["bmi"]), 1) if pd.notna(last["bmi"]) else None,
        "whtr": round(float(last["whtr"]), 3) if pd.notna(last["whtr"]) else None,
        "weight_change_kg": round(float(last["weight_kg"] - first["weight_kg"]), 1)
        if pd.notna(last["weight_kg"]) and pd.notna(first["weight_kg"])
        else None,
        "waist_change_cm": round(float(last["waist_cm"] - first["waist_cm"]), 1)
        if pd.notna(last["waist_cm"]) and pd.notna(first["waist_cm"])
        else None,
    }
