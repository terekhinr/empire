#!/usr/bin/env python3
"""Health data analysis from data/pension/body — charts and statistics."""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from scipy import stats

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "pension" / "body"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "pension" / "body" / "analysis_report"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# User profile (current)
AGE = 48
HEIGHT_CM = 186
CURRENT_WEIGHT = 111.1
CURRENT_WAIST = 103.5
WEIGHT_MIN = 90
WEIGHT_MAX = 120

plt.rcParams.update({
    "figure.facecolor": "#fafafa",
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#cccccc",
    "axes.labelcolor": "#333333",
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "font.size": 10,
    "legend.framealpha": 0.9,
    "figure.dpi": 120,
})

COLORS = {
    "weight": "#2563eb",
    "fat": "#dc2626",
    "muscle": "#16a34a",
    "visceral": "#ea580c",
    "calories_in": "#7c3aed",
    "calories_out": "#0891b2",
    "running": "#0d9488",
    "protein": "#ca8a04",
}


def parse_ru_number(val) -> float:
    if pd.isna(val) or val in ("--", ""):
        return np.nan
    s = str(val).strip().replace(",", ".")
  # remove thousands sep in steps like "12,308"
    if re.match(r"^\d{1,3}(,\d{3})+$", str(val).strip()):
        s = str(val).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_duration_minutes(val) -> float:
    if pd.isna(val) or val == "--":
        return np.nan
    s = str(val).strip()
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
        pass
    return np.nan


def load_body() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "BODY_1770152199658.csv")
    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert(None)
    for col in ["weight", "height", "bmi", "fatRate", "bodyWaterRate", "boneMass",
                "metabolism", "muscleRate", "visceralFat"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[(df["weight"] >= WEIGHT_MIN) & (df["weight"] <= WEIGHT_MAX)].copy()
    return df


def load_food() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "food.csv")
    df["date"] = pd.to_datetime(df["date"])
    for col in ["calories", "protein", "fat", "carbs"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_activities() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "Activities (6).csv")
    df["date"] = pd.to_datetime(df["Дата"])
    df["distance_km"] = df["Расстояние"].apply(parse_ru_number)
    df["calories"] = df["Калории"].apply(parse_ru_number)
    df["duration_min"] = df["Время"].apply(parse_duration_minutes)
    df["avg_hr"] = df["Средняя ЧП"].apply(parse_ru_number)
    return df


def daily_body(df: pd.DataFrame) -> pd.DataFrame:
    d = df.set_index("time").resample("D").agg({
        "weight": "mean",
        "fatRate": "mean",
        "muscleRate": "mean",
        "visceralFat": "mean",
        "metabolism": "mean",
        "bodyWaterRate": "mean",
    }).dropna(subset=["weight"])
    d["fat_mass_kg"] = d["weight"] * d["fatRate"] / 100
    d["muscle_mass_kg"] = d["weight"] * d["muscleRate"] / 100
    d["lean_mass_kg"] = d["weight"] - d["fat_mass_kg"]
    d["ffmi_proxy"] = d["lean_mass_kg"] / ((HEIGHT_CM / 100) ** 2)
    return d.reset_index().rename(columns={"time": "date"})


def monthly_smooth(series: pd.Series, window: int = 30) -> pd.Series:
    return series.rolling(window=window, min_periods=max(7, window // 4), center=True).mean()


def plot_weight_trend(daily: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.scatter(daily["date"], daily["weight"], s=8, alpha=0.25, color=COLORS["weight"], label="Ежедневно")
    smooth = monthly_smooth(daily.set_index("date")["weight"], 60)
    ax.plot(smooth.index, smooth.values, color=COLORS["weight"], linewidth=2.5, label="Сглаживание 60 дн.")
    ax.axhline(CURRENT_WEIGHT, color="#9333ea", linestyle=":", linewidth=1.5, label=f"Сейчас {CURRENT_WEIGHT} кг")
    ax.set_title("Динамика веса (2016–2026), без выбросов <90 и >120 кг")
    ax.set_xlabel("Дата")
    ax.set_ylabel("Вес, кг")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    plt.xticks(rotation=45)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "01_weight_trend.png", bbox_inches="tight")
    plt.close(fig)


def plot_body_composition(daily: pd.DataFrame) -> None:
    comp = daily.dropna(subset=["fatRate", "muscleRate"])
    comp = comp[comp["fatRate"] > 0]
    if comp.empty:
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    ax = axes[0, 0]
    ax.plot(comp["date"], comp["fatRate"], color=COLORS["fat"], alpha=0.5, linewidth=1)
    ax.plot(comp["date"], monthly_smooth(comp.set_index("date")["fatRate"], 30).values,
            color=COLORS["fat"], linewidth=2, label="% жира")
    ax.set_title("% жира")
    ax.set_ylabel("%")

    ax = axes[0, 1]
    ax.plot(comp["date"], comp["muscleRate"], color=COLORS["muscle"], alpha=0.5, linewidth=1)
    ax.plot(comp["date"], monthly_smooth(comp.set_index("date")["muscleRate"], 30).values,
            color=COLORS["muscle"], linewidth=2, label="% мышц (по весам)")
    ax.set_title("% мышечной массы (биоимпеданс)")
    ax.set_ylabel("%")

    ax = axes[1, 0]
    ax.plot(comp["date"], comp["fat_mass_kg"], color=COLORS["fat"], linewidth=1.5, label="Жир, кг")
    ax.plot(comp["date"], comp["muscle_mass_kg"], color=COLORS["muscle"], linewidth=1.5, label="Мышцы, кг")
    ax.set_title("Абсолютные массы жира и мышц")
    ax.set_ylabel("кг")
    ax.legend()

    ax = axes[1, 1]
    ax.plot(comp["date"], comp["visceralFat"], color=COLORS["visceral"], linewidth=1.5)
    ax.axhline(12, color="red", linestyle="--", alpha=0.6, label="Риск >12")
    ax.set_title("Висцеральный жир (шкала весов)")
    ax.set_ylabel("уровень")
    ax.legend()

    for ax in axes.flat:
        ax.set_xlabel("Дата")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.suptitle("Состав тела (биоимпедансные весы)", y=1.01, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "02_body_composition.png", bbox_inches="tight")
    plt.close(fig)


def plot_food(daily_food: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    ax = axes[0, 0]
    ax.bar(daily_food["date"], daily_food["calories"], width=1, color=COLORS["calories_in"], alpha=0.6)
    ax.axhline(daily_food["calories"].median(), color="black", linestyle="--",
               label=f"Медиана {daily_food['calories'].median():.0f} ккал")
    ax.set_title("Калории в день (дневник питания)")
    ax.set_ylabel("ккал/день")
    ax.legend()

    monthly = daily_food.set_index("date").resample("ME").mean(numeric_only=True)
    ax = axes[0, 1]
    ax.plot(monthly.index, monthly["calories"], marker="o", color=COLORS["calories_in"])
    ax.set_title("Средние калории по месяцам")
    ax.set_ylabel("ккал/день")

    ax = axes[1, 0]
    ax.stackplot(
        monthly.index,
        monthly["protein"] * 4,
        monthly["fat"] * 9,
        monthly["carbs"] * 4,
        labels=["Белки", "Жиры", "Углеводы"],
        colors=["#22c55e", "#f59e0b", "#3b82f6"],
        alpha=0.75,
    )
    ax.set_title("Макронутриенты по месяцам (ккал)")
    ax.legend(loc="upper left")

    ax = axes[1, 1]
    pct_p = monthly["protein"] * 4 / monthly["calories"] * 100
    pct_f = monthly["fat"] * 9 / monthly["calories"] * 100
    pct_c = monthly["carbs"] * 4 / monthly["calories"] * 100
    ax.plot(monthly.index, pct_p, label="Белки %", color="#22c55e")
    ax.plot(monthly.index, pct_f, label="Жиры %", color="#f59e0b")
    ax.plot(monthly.index, pct_c, label="Углеводы %", color="#3b82f6")
    ax.set_title("Доля макронутриентов")
    ax.set_ylabel("% от калорий")
    ax.legend()

    for ax in axes.flat:
        ax.set_xlabel("Дата")
    fig.suptitle("Питание (дневник)", y=1.01, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "03_nutrition.png", bbox_inches="tight")
    plt.close(fig)


def plot_activities(act: pd.DataFrame) -> None:
    runs = act[act["Тип занятия"].str.contains("Бег", na=False)].copy()
    monthly_run = runs.set_index("date").resample("ME").agg(
        distance_km=("distance_km", "sum"),
        calories=("calories", "sum"),
        sessions=("distance_km", "count"),
        duration_min=("duration_min", "sum"),
    )

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    ax = axes[0, 0]
    ax.bar(monthly_run.index, monthly_run["distance_km"], width=20, color=COLORS["running"], alpha=0.75)
    ax.set_title("Бег: км в месяц")
    ax.set_ylabel("км")

    ax = axes[0, 1]
    ax.bar(monthly_run.index, monthly_run["calories"], width=20, color=COLORS["calories_out"], alpha=0.75)
    ax.set_title("Бег: калории в месяц (Garmin)")
    ax.set_ylabel("ккал")

    all_monthly = act.set_index("date").resample("ME").agg(
        calories=("calories", "sum"),
        duration_min=("duration_min", "sum"),
    )
    ax = axes[1, 0]
    ax.plot(all_monthly.index, all_monthly["calories"], color=COLORS["calories_out"], marker="o")
    ax.set_title("Все активности: калории/месяц")
    ax.set_ylabel("ккал")

    ax = axes[1, 1]
    type_cal = act.groupby("Тип занятия")["calories"].sum().sort_values(ascending=True)
    ax.barh(type_cal.index, type_cal.values, color="#64748b")
    ax.set_title("Калории по типам активности (всего)")
    ax.set_xlabel("ккал")

    for ax in axes.flat[:3]:
        ax.set_xlabel("Дата")
    fig.suptitle("Физическая активность", y=1.01, fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "04_activities.png", bbox_inches="tight")
    plt.close(fig)


def plot_energy_balance(daily_food: pd.DataFrame, act: pd.DataFrame, daily_body: pd.DataFrame) -> None:
    food_m = daily_food.set_index("date").resample("ME").mean(numeric_only=True)["calories"]
    act_m = act.set_index("date").resample("ME").sum(numeric_only=True)["calories"]
    # BMR estimate Mifflin-St Jeor male
    bmr = 10 * CURRENT_WEIGHT + 6.25 * HEIGHT_CM - 5 * AGE + 5

    merged = pd.DataFrame({"intake": food_m, "activity": act_m}).dropna(how="all")
    merged = merged.dropna(subset=["intake"])
    merged["activity"] = merged["activity"].fillna(0)
    merged["estimated_tdee"] = bmr * 1.35 + merged["activity"] / 30  # rough daily from monthly act

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(merged.index, merged["intake"], label="Питание (средн./день в месяце)", color=COLORS["calories_in"], linewidth=2)
    ax.plot(merged.index, merged["estimated_tdee"], label="Оценка расхода (BMR×1.35 + акт./день)", color=COLORS["calories_out"], linewidth=2, linestyle="--")
    ax.axhline(bmr, color="gray", linestyle=":", label=f"BMR ≈ {bmr:.0f} ккал")
    ax.set_title("Энергетический баланс (оценочно, 2022–2026)")
    ax.set_ylabel("ккал/день")
    ax.set_xlabel("Дата")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "05_energy_balance.png", bbox_inches="tight")
    plt.close(fig)


def plot_correlation(daily: pd.DataFrame, daily_food: pd.DataFrame, act: pd.DataFrame) -> pd.DataFrame:
    body_m = daily.set_index("date").resample("ME").mean(numeric_only=True)
    food_m = daily_food.set_index("date").resample("ME").mean(numeric_only=True)
    run = act[act["Тип занятия"].str.contains("Бег", na=False)]
    run_m = run.set_index("date").resample("ME").agg(distance_km=("distance_km", "sum"), run_cal=("calories", "sum"))

    merged = body_m.join(food_m.add_prefix("food_"), how="outer").join(run_m, how="outer")
    cols = [c for c in merged.columns if merged[c].notna().sum() >= 12]
    sub = merged[cols].dropna(thresh=len(cols) // 2)
    corr = sub.corr(method="pearson", min_periods=8)

    fig, ax = plt.subplots(figsize=(12, 10))
    im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)
    for i in range(len(corr)):
        for j in range(len(corr)):
            v = corr.iloc[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if abs(v) > 0.5 else "black")
    plt.colorbar(im, ax=ax, fraction=0.046)
    ax.set_title("Корреляция Пирсона (месячные данные)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "06_correlation_matrix.png", bbox_inches="tight")
    plt.close(fig)
    return corr


def find_best_composition(daily: pd.DataFrame) -> dict:
    comp = daily.dropna(subset=["fatRate", "muscleRate"])
    comp = comp[(comp["fatRate"] > 0) & (comp["muscleRate"] > 0)].copy()
    # Best = lowest fat% with highest muscle mass, composite score
    comp["score"] = comp["muscle_mass_kg"] / comp["fat_mass_kg"]
    best_score = comp.loc[comp["score"].idxmax()]
    lowest_fat = comp.loc[comp["fatRate"].idxmin()]
    highest_muscle = comp.loc[comp["muscle_mass_kg"].idxmax()]
    return {
        "best_ratio": {
            "date": str(best_score["date"].date()),
            "weight": round(best_score["weight"], 1),
            "fat_pct": round(best_score["fatRate"], 1),
            "muscle_pct": round(best_score["muscleRate"], 1),
            "fat_kg": round(best_score["fat_mass_kg"], 1),
            "muscle_kg": round(best_score["muscle_mass_kg"], 1),
            "visceral": round(best_score["visceralFat"], 1) if pd.notna(best_score["visceralFat"]) else None,
        },
        "lowest_fat": {
            "date": str(lowest_fat["date"].date()),
            "weight": round(lowest_fat["weight"], 1),
            "fat_pct": round(lowest_fat["fatRate"], 1),
            "muscle_kg": round(lowest_fat["muscle_mass_kg"], 1),
        },
        "highest_muscle": {
            "date": str(highest_muscle["date"].date()),
            "weight": round(highest_muscle["weight"], 1),
            "muscle_kg": round(highest_muscle["muscle_mass_kg"], 1),
            "fat_pct": round(highest_muscle["fatRate"], 1),
        },
    }


def compute_stats(body_raw: pd.DataFrame, daily: pd.DataFrame, food: pd.DataFrame,
                  daily_food: pd.DataFrame, act: pd.DataFrame, corr: pd.DataFrame) -> dict:
    runs = act[act["Тип занятия"].str.contains("Бег", na=False)]
    bmr = 10 * CURRENT_WEIGHT + 6.25 * HEIGHT_CM - 5 * AGE + 5
    bmi = CURRENT_WEIGHT / ((HEIGHT_CM / 100) ** 2)

    w_start = daily["weight"].iloc[0]
    w_end = daily["weight"].iloc[-1]
    w_min_row = daily.loc[daily["weight"].idxmin()]
    w_max_row = daily.loc[daily["weight"].idxmax()]

    removed = 1000 - len(body_raw)  # original count known

    yearly = daily.set_index("date")["weight"].resample("YE").mean()

    return {
        "profile": {
            "age": AGE, "height_cm": HEIGHT_CM, "weight_kg": CURRENT_WEIGHT,
            "waist_cm": CURRENT_WAIST, "bmi": round(bmi, 1),
            "bmr_kcal": round(bmr),
            "tdee_sedentary": round(bmr * 1.2),
            "tdee_active": round(bmr * 1.55),
        },
        "weight": {
            "period": f"{daily['date'].min().date()} — {daily['date'].max().date()}",
            "outliers_removed": removed,
            "start_kg": round(w_start, 1),
            "end_kg": round(w_end, 1),
            "change_kg": round(w_end - w_start, 1),
            "min_kg": round(w_min_row["weight"], 1),
            "min_date": str(w_min_row["date"].date()),
            "max_kg": round(w_max_row["weight"], 1),
            "max_date": str(w_max_row["date"].date()),
            "yearly_avg": {str(k.year): round(v, 1) for k, v in yearly.items()},
        },
        "composition": find_best_composition(daily),
        "nutrition": {
            "days_logged": len(daily_food),
            "avg_calories": round(daily_food["calories"].mean()),
            "median_calories": round(daily_food["calories"].median()),
            "avg_protein_g": round(daily_food["protein"].mean(), 1),
            "avg_fat_g": round(daily_food["fat"].mean(), 1),
            "avg_carbs_g": round(daily_food["carbs"].mean(), 1),
            "protein_per_kg": round(daily_food["protein"].mean() / CURRENT_WEIGHT, 2),
        },
        "running": {
            "total_sessions": len(runs),
            "total_distance_km": round(runs["distance_km"].sum(), 1),
            "total_calories": round(runs["calories"].sum()),
            "total_hours": round(runs["duration_min"].sum() / 60, 1),
            "avg_distance_per_run": round(runs["distance_km"].mean(), 2),
            "avg_pace_min_per_km": round(runs["duration_min"].sum() / runs["distance_km"].sum(), 2) if runs["distance_km"].sum() > 0 else None,
        },
        "all_activities": {
            "total_sessions": len(act),
            "total_calories": round(act["calories"].sum()),
            "total_hours": round(act["duration_min"].sum() / 60, 1),
            "by_type": act.groupby("Тип занятия").agg(
                sessions=("calories", "count"),
                km=("distance_km", "sum"),
                kcal=("calories", "sum"),
            ).to_dict(),
        },
        "key_correlations": {
            "weight_vs_food_cal": round(corr.loc["weight", "food_calories"], 3) if "food_calories" in corr.index and "weight" in corr.index else None,
            "weight_vs_run_km": round(corr.loc["weight", "distance_km"], 3) if "distance_km" in corr.index else None,
            "fat_vs_food_cal": round(corr.loc["fatRate", "food_calories"], 3) if "food_calories" in corr.index and "fatRate" in corr.index else None,
        },
    }


def main() -> None:
    body = load_body()
    food = load_food()
    act = load_activities()
    daily = daily_body(body)
    daily_food = food.groupby("date").agg(
        calories=("calories", "sum"),
        protein=("protein", "sum"),
        fat=("fat", "sum"),
        carbs=("carbs", "sum"),
    ).reset_index()

    plot_weight_trend(daily)
    plot_body_composition(daily)
    plot_food(daily_food)
    plot_activities(act)
    plot_energy_balance(daily_food, act, daily)
    corr = plot_correlation(daily, daily_food, act)
    stats_out = compute_stats(body, daily, food, daily_food, act, corr)

    with open(OUT_DIR / "statistics.json", "w", encoding="utf-8") as f:
        json.dump(stats_out, f, ensure_ascii=False, indent=2)

    print(json.dumps(stats_out, ensure_ascii=False, indent=2))
    print(f"\nCharts saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
