"""Streamlit page: health tracking (measurements, strength, CSV sync)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from health_db import (
    DEFAULT_HEIGHT_CM,
    STRENGTH_EXERCISES,
    WEIGHT_MAX_KG,
    WEIGHT_MIN_KG,
    add_measurement,
    add_strength_log,
    import_activities_csv,
    import_body_scale_csv,
    import_food_csv,
    latest_measurement_summary,
    load_activities_monthly,
    load_body_scale_daily,
    load_food_daily,
    load_import_meta,
    load_measurements_df,
    load_strength_df,
    measurements_daily_summary,
    prepare_chart_frame,
    seed_measurements_if_empty,
    smooth_series,
    sync_all_csv,
    sync_csv_if_changed,
)
from health_workout_program import (
    get_calendar,
    get_session_for_date,
    next_scheduled_session,
    program_summary,
)
from intervals_sync import intervals_config, should_sync_intervals, sync_intervals

MOBILE_CSS = """
<style>
@media (max-width: 768px) {
    .block-container { padding-top: 1rem; padding-left: 0.75rem; padding-right: 0.75rem; }
    [data-testid="stMetric"] { background: rgba(240,240,240,0.35); padding: 0.5rem; border-radius: 0.5rem; }
    [data-testid="stMetricValue"] { font-size: 1.35rem !important; }
    [data-testid="column"] { min-width: 0 !important; }
    div[data-testid="stHorizontalBlock"] { gap: 0.4rem; }
}
.health-note { color: #666; font-size: 0.9rem; }
</style>
"""


def _inject_mobile_css() -> None:
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


def _plotly_smooth_line(
    df: pd.DataFrame,
    x: str,
    y_raw: str,
    y_smooth: str,
    title: str,
    color: str = "#2563eb",
    *,
    outlier_note: str | None = None,
) -> None:
    if df.empty or y_smooth not in df.columns or df[y_smooth].dropna().empty:
        return
    fig = go.Figure()
    if y_raw in df.columns and df[y_raw].notna().any():
        fig.add_trace(
            go.Scatter(
                x=df[x],
                y=df[y_raw],
                mode="markers",
                name="замеры",
                marker=dict(size=5, color=color, opacity=0.22),
                hovertemplate="%{y:.1f}<extra></extra>",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y_smooth],
            mode="lines",
            name="тренд",
            line=dict(color=color, width=2.8, shape="spline", smoothing=1.2),
            hovertemplate="%{y:.1f}<extra></extra>",
        )
    )
    subtitle = outlier_note or ""
    fig.update_layout(
        title=dict(text=f"{title}<br><sup style='color:#888;font-size:11px'>{subtitle}</sup>", x=0),
        height=320,
        margin=dict(l=10, r=10, t=52, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis_title="",
        yaxis_title="",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


def _build_body_chart_df(daily: pd.DataFrame, scale_daily: pd.DataFrame) -> pd.DataFrame:
    chart_df = daily.copy()
    if not scale_daily.empty:
        merged = chart_df.merge(scale_daily, on="date", how="outer").sort_values("date")
        merged["weight_plot"] = merged["weight_kg"]
        if "scale_weight_kg" in merged.columns:
            merged["weight_plot"] = merged["weight_plot"].fillna(merged["scale_weight_kg"])
        chart_df = merged
    else:
        chart_df["weight_plot"] = chart_df["weight_kg"]

    return prepare_chart_frame(
        chart_df,
        smooth_cols=["weight_plot", "waist_cm", "biceps_avg_cm", "legs_cm", "fat_pct", "visceral"],
        smooth_window=5,
        weight_cols=["weight_kg", "weight_plot", "scale_weight_kg"],
    )


def _last_weight_for_exercise(exercise_key: str) -> float | None:
    df = load_strength_df()
    if df.empty:
        return None
    sub = df[df["exercise_key"] == exercise_key]
    if sub.empty:
        return None
    return float(sub.loc[sub["weight_kg"].idxmax(), "weight_kg"])


def _workout_banner() -> None:
    today = date.today()
    session = get_session_for_date(today)
    if session and session.template:
        tpl = session.template
        st.success(
            f"**Сегодня:** {session.label} — {tpl.title} · "
            f"вкладка «Программа» для записи подходов"
        )
        if session.note:
            st.caption(session.note)
        if tpl.meta.get("калории"):
            st.caption(f"Калории: {tpl.meta['калории']}")
    else:
        nxt = next_scheduled_session(today)
        if nxt:
            st.info(f"Сегодня нет тренировки по календарю. Ближайшая: **{nxt.on}** — {nxt.label}")


def _tab_program() -> None:
    summary = program_summary()
    if not summary["calendar_days"]:
        st.warning(f"Файл программы не найден: `{summary['path']}`")
        return

    st.caption(
        f"Макроцикл {summary['start']} — {summary['end']} · "
        f"{summary['calendar_days']} тренировок · {summary['phases']} фазы"
    )

    session_date = st.date_input("Дата тренировки", value=date.today(), key="program_date")
    session = get_session_for_date(session_date)
    if not session:
        st.info("На эту дату в календаре нет тренировки. Выберите другую дату или смотрите расписание ниже.")
    elif not session.template:
        st.warning(f"{session.label} — шаблон не найден в файле программы.")
    elif session.template.exercises and all(ex.is_rest for ex in session.template.exercises):
        st.info(f"**{session.label}** — день отдыха. {session.template.exercises[0].detail}")
    elif session.template:
        tpl = session.template
        st.subheader(f"{session.label}: {tpl.title}")
        if tpl.meta:
            with st.expander("Питание и фаза", expanded=False):
                for k, v in tpl.meta.items():
                    st.markdown(f"**{k}:** {v}")
        if session.note:
            st.caption(session.note)

        strength_today = load_strength_df()
        if not strength_today.empty:
            strength_today = strength_today[
                strength_today["logged_on"].dt.date == session_date
            ]

        with st.form("program_workout_log"):
            st.markdown("Разверните упражнение — отдельная строка на каждый подход.")
            to_save: list[tuple] = []
            for i, ex in enumerate(tpl.exercises):
                if ex.is_rest:
                    continue
                default_w = ex.suggested_weight_kg
                if default_w is None:
                    default_w = _last_weight_for_exercise(ex.exercise_key) or 0.0
                default_reps = ex.reps or ex.reps_max or ex.reps_min or 10
                n_sets = 1 if ex.is_max else max(1, ex.sets or 1)
                hint = ex.prescription
                if ex.detail:
                    hint += f" · {ex.detail}"
                with st.expander(f"{ex.exercise_label} — {ex.prescription}", expanded=(i == 0)):
                    st.caption(hint)
                    shared_w = None
                    if n_sets > 1:
                        shared_w = st.number_input(
                            "Вес, кг (все подходы)",
                            min_value=0.0,
                            max_value=500.0,
                            value=float(default_w),
                            step=2.5,
                            key=f"prog_shared_w_{i}",
                        )
                    for s in range(1, n_sets + 1):
                        c0, c1, c2 = st.columns([1, 2, 2])
                        with c0:
                            done = st.checkbox("✓", value=True, key=f"prog_done_{i}_{s}", label_visibility="collapsed")
                        with c1:
                            if n_sets == 1:
                                w = st.number_input(
                                    "кг",
                                    min_value=0.0,
                                    max_value=500.0,
                                    value=float(default_w),
                                    step=2.5,
                                    key=f"prog_w_{i}_{s}",
                                    label_visibility="collapsed",
                                )
                            else:
                                w = shared_w
                        with c2:
                            reps = st.number_input(
                                "повт",
                                min_value=1,
                                max_value=50,
                                value=int(default_reps),
                                key=f"prog_r_{i}_{s}",
                                label_visibility="collapsed",
                            )
                        if done:
                            note = f"подход {s}/{n_sets}"
                            to_save.append((ex.exercise_key, float(w or 0), int(reps), 1, note))

            if st.form_submit_button("Сохранить тренировку", type="primary"):
                if not to_save:
                    st.warning("Отметьте хотя бы один подход.")
                else:
                    for key, w, reps, sets, note in to_save:
                        add_strength_log(
                            session_date.isoformat(),
                            key,
                            weight_kg=w,
                            reps=reps,
                            sets=sets,
                            note=note,
                        )
                    st.success(f"Сохранено подходов: {len(to_save)}")
                    st.rerun()

        if not strength_today.empty:
            st.markdown("**Уже записано в этот день:**")
            st.dataframe(
                strength_today[
                    ["exercise_label", "weight_kg", "reps", "sets", "note"]
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.divider()
    st.subheader("Календарь")
    rows = []
    for entry in get_calendar():
        mark = "→" if entry.on == session_date else ""
        rows.append(
            {
                "": mark,
                "Дата": entry.on.isoformat(),
                "Тренировка": entry.label,
                "Примечание": entry.note,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _tab_overview(daily: pd.DataFrame, scale_daily: pd.DataFrame) -> None:
    _workout_banner()
    summary = latest_measurement_summary()
    if summary:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Вес", f"{summary.get('weight_kg', '—')} кг", summary.get("weight_change_kg"))
        c2.metric("Талия", f"{summary.get('waist_cm', '—')} см", summary.get("waist_change_cm"))
        c3.metric("ИМТ", summary.get("bmi", "—"))
        c4.metric("WHtR", summary.get("whtr", "—"))
        st.caption(
            f"Последний замер: {summary.get('date')} · рост {DEFAULT_HEIGHT_CM:.0f} см · "
            "WHtR >0.5 — повышенный риск"
        )
    else:
        st.info("Добавьте первый замер во вкладке «Записать».")

    chart_df = _build_body_chart_df(daily, scale_daily)
    outlier_note = f"вес вне {WEIGHT_MIN_KG:.0f}–{WEIGHT_MAX_KG:.0f} кг скрыт · линия сглажена (5 точек)"

    left, right = st.columns(2)
    with left:
        _plotly_smooth_line(
            chart_df, "date", "weight_plot_raw", "weight_plot_smooth",
            "Вес (ручные замеры + весы)", "#2563eb", outlier_note=outlier_note,
        )
    with right:
        _plotly_smooth_line(
            chart_df, "date", "waist_cm_raw", "waist_cm_smooth",
            "Талия, см", "#dc2626",
        )

    left2, right2 = st.columns(2)
    with left2:
        _plotly_smooth_line(
            chart_df, "date", "biceps_avg_cm_raw", "biceps_avg_cm_smooth",
            "Бицепс (средний), см", "#16a34a",
        )
    with right2:
        _plotly_smooth_line(
            chart_df, "date", "legs_cm_raw", "legs_cm_smooth",
            "Ноги, см", "#7c3aed",
        )

    if not scale_daily.empty and scale_daily["fat_pct"].notna().any():
        st.subheader("Данные умных весов")
        scale_chart = prepare_chart_frame(
            scale_daily, smooth_cols=["fat_pct", "visceral"], smooth_window=7,
        )
        s1, s2 = st.columns(2)
        with s1:
            _plotly_smooth_line(
                scale_chart, "date", "fat_pct_raw", "fat_pct_smooth",
                "% жира (весы)", "#ea580c",
            )
        with s2:
            _plotly_smooth_line(
                scale_chart, "date", "visceral_raw", "visceral_smooth",
                "Висцеральный жир", "#b45309",
            )

    food = load_food_daily()
    if not food.empty:
        st.subheader("Питание (импорт CSV)")
        food_m = food.set_index("day").resample("ME").mean(numeric_only=True).reset_index()
        food_m["calories_smooth"] = smooth_series(food_m["calories"], window=3)
        _plotly_smooth_line(
            food_m, "day", "calories", "calories_smooth",
            "Средние калории/день по месяцам", "#7c3aed",
        )

    act_m = load_activities_monthly()
    if not act_m.empty:
        runs = act_m[act_m["activity_type"].str.contains("Бег", na=False)]
        if not runs.empty:
            runs = runs.groupby("month", as_index=False).agg(distance_km=("distance_km", "sum"))
            runs["month"] = pd.to_datetime(runs["month"] + "-01")
            runs["distance_smooth"] = smooth_series(runs["distance_km"], window=3)
            st.subheader("Бег (Garmin CSV)")
            _plotly_smooth_line(
                runs, "month", "distance_km", "distance_smooth",
                "Км бега в месяц", "#0d9488",
            )


def _tab_log_entry() -> None:
    st.subheader("Новый замер тела")
    with st.form("health_measurement_form", clear_on_submit=True):
        measured_on = st.date_input("Дата", value=date.today())
        c1, c2 = st.columns(2)
        with c1:
            weight = st.number_input("Вес, кг", min_value=50.0, max_value=200.0, value=111.1, step=0.1)
            waist = st.number_input("Талия, см", min_value=60.0, max_value=160.0, value=103.5, step=0.1)
            legs = st.number_input("Ноги, см", min_value=40.0, max_value=90.0, value=66.0, step=0.5)
        with c2:
            biceps_r = st.number_input("Бицепс правый, см", min_value=20.0, max_value=60.0, value=42.0, step=0.5)
            biceps_l = st.number_input("Бицепс левый, см", min_value=20.0, max_value=60.0, value=42.0, step=0.5)
            note = st.text_input("Заметка", value="")
        submitted = st.form_submit_button("Сохранить замер", type="primary")
        if submitted:
            add_measurement(
                measured_on.isoformat(),
                weight_kg=weight,
                waist_cm=waist,
                biceps_r_cm=biceps_r,
                biceps_l_cm=biceps_l,
                legs_cm=legs,
                note=note or None,
            )
            st.success("Замер сохранён.")
            st.rerun()

    st.divider()
    st.subheader("Силовая тренировка")
    with st.form("health_strength_form", clear_on_submit=True):
        logged_on = st.date_input("Дата тренировки", value=date.today(), key="strength_date")
        exercise = st.selectbox(
            "Упражнение",
            options=list(STRENGTH_EXERCISES.keys()),
            format_func=lambda k: STRENGTH_EXERCISES[k],
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            w = st.number_input("Вес, кг", min_value=0.0, max_value=500.0, value=100.0, step=2.5)
        with c2:
            reps = st.number_input("Повторения", min_value=1, max_value=30, value=10)
        with c3:
            sets = st.number_input("Подходы", min_value=1, max_value=10, value=3)
        s_note = st.text_input("Заметка к подходу", value="", key="strength_note")
        s_sub = st.form_submit_button("Сохранить силовую", type="primary")
        if s_sub:
            add_strength_log(
                logged_on.isoformat(),
                exercise,
                weight_kg=w,
                reps=int(reps),
                sets=int(sets),
                note=s_note or None,
            )
            st.success("Силовая запись сохранена.")
            st.rerun()


def _tab_strength() -> None:
    df = load_strength_df()
    if df.empty:
        st.info("Пока нет записей силовых. Добавьте во вкладке «Записать».")
        return

    st.caption("Прогрессия: +2.5–5 кг, когда 2 тренировки подряд все подходы в верхней границе повторений.")
    for key, label in STRENGTH_EXERCISES.items():
        sub = df[df["exercise_key"] == key].copy()
        if sub.empty:
            continue
        best = sub.loc[sub["weight_kg"].idxmax()]
        st.markdown(f"**{label}** — лучший вес: {best['weight_kg']:.1f} кг × {int(best['reps'])} "
                    f"({best['logged_on'].date()})")
        chart = sub.groupby(sub["logged_on"].dt.date, as_index=False)["weight_kg"].max()
        chart.rename(columns={"logged_on": "date"}, inplace=True)
        chart["date"] = pd.to_datetime(chart["date"])
        chart = prepare_chart_frame(chart, smooth_cols=["weight_kg"], smooth_window=3)
        _plotly_smooth_line(
            chart, "date", "weight_kg_raw", "weight_kg_smooth",
            f"{label}: макс. вес по дню", "#0891b2",
        )

    st.dataframe(
        df[["logged_on", "exercise_label", "weight_kg", "reps", "sets", "note"]].sort_values(
            "logged_on", ascending=False
        ),
        use_container_width=True,
        hide_index=True,
    )


def _tab_history(daily: pd.DataFrame) -> None:
    raw = load_measurements_df()
    if raw.empty:
        st.info("Нет замеров.")
        return
    show = raw.copy()
    show["measured_on"] = show["measured_on"].dt.date
    sort_cols = ["measured_on"]
    if "id" in show.columns:
        sort_cols.append("id")
    show = show.sort_values(sort_cols, ascending=[False] * len(sort_cols))
    display_cols = [
        "measured_on",
        "weight_kg",
        "waist_cm",
        "biceps_r_cm",
        "biceps_l_cm",
        "legs_cm",
        "note",
        "source",
    ]
    st.dataframe(
        show[display_cols],
        use_container_width=True,
        hide_index=True,
    )
    if not daily.empty:
        st.download_button(
            "Скачать сводку CSV",
            daily.to_csv(index=False).encode("utf-8"),
            file_name="health_measurements_daily.csv",
            mime="text/csv",
        )


def _tab_import() -> None:
    st.subheader("Синхронизация")
    with st.expander("📱 Настройка Zepp Life (вес) и Lifesum (еда)", expanded=False):
        st.markdown(
            """
**Zepp Life → Google Fit → Intervals** (у вас Google Fit уже в Intervals):
1. Zepp Life → **Профиль** → **Add accounts** → **Google Fit** → Разрешить
2. После взвешивания вес уйдёт в Google Fit → Intervals → дашборд (кнопка Intervals ниже)

**Lifesum → Health Connect → VPS** (автоматические калории):
1. Установить **Health Connect** (Play Store)
2. Lifesum → **Настройки** → **Automatic Tracking** → **Health Connect** → экспорт питания
3. Отключить **Multimodal Tracking** в дневнике Lifesum
4. Установить **[HC Webhook](https://hcwebhook.com/android)**:
   - URL: `https://neverretire.ru/api/health/ingest`
   - Заголовок: `X-Health-Token` = токен из `.env` (`HEALTH_INGEST_TOKEN`)
   - Типы: **Nutrition**, **Weight**, **Body fat**
   - Интервал: 30–60 мин
5. Google Fit → **Профиль** → **Sync Fit with Health Connect** (для веса из Zepp)

**Запасной путь:** CSV → Яндекс.Диск `Empire/health-inbox/` (кнопки ниже).
            """
        )

    st.markdown(
        '<p class="health-note">Авто: <b>Intervals.icu</b> (Garmin), <b>Health Connect webhook</b> (Lifesum). '
        "CSV из <code>data/pension/body/</code> — при изменении файлов.</p>",
        unsafe_allow_html=True,
    )

    if intervals_config():
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("Синхронизировать Intervals.icu", type="primary"):
                with st.spinner("Intervals.icu…"):
                    result = sync_intervals(force=True)
                if result.get("ok"):
                    st.success(result)
                else:
                    st.error(result)
        with c2:
            st.caption("Garmin → Intervals.icu → VPS. Тренировки и вес (wellness), без Health Connect.")
    else:
        st.info("Intervals.icu: добавьте `INTERVALS_ICU_API_KEY` и `INTERVALS_ICU_ATHLETE_ID` в `.env`.")

    meta = load_import_meta()
    if meta:
        st.write("Последний импорт:")
        for k, v in meta.items():
            st.caption(f"**{k}**: {v}")

    if st.button("Синхронизировать все CSV", type="primary"):
        with st.spinner("Импорт…"):
            result = sync_csv_if_changed(force=True) or sync_all_csv()
        st.success(result)
        st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Только весы"):
            st.write(import_body_scale_csv())
    with c2:
        if st.button("Только питание"):
            st.write(import_food_csv())
    with c3:
        if st.button("Только Garmin"):
            st.write(import_activities_csv())

    seeded = seed_measurements_if_empty()
    if seeded:
        st.info(f"Загружено исторических замеров из seed: {seeded}")


def page_health() -> None:
    _inject_mobile_css()
    st.header("🩺 Здоровье")
    st.caption("Замеры, силовые, импорт весов/питания/Garmin · мобильный браузер OK")

    seed_measurements_if_empty()
    auto = sync_csv_if_changed()
    if auto:
        changed = ", ".join(auto.get("changed") or []) or "файлы"
        st.toast(f"Обновлены данные: {changed}", icon="🔄")
    if intervals_config() and should_sync_intervals():
        icu_auto = sync_intervals()
        if icu_auto.get("ok") and not icu_auto.get("skipped") and (
            icu_auto.get("activities", {}).get("imported") or icu_auto.get("wellness", {}).get("imported")
        ):
            st.toast("Обновлены данные Intervals.icu", icon="🏃")

    daily = measurements_daily_summary()
    scale_daily = load_body_scale_daily()

    tab_overview, tab_program, tab_log, tab_strength, tab_history, tab_import = st.tabs(
        ["Обзор", "Программа", "Записать", "Силовые", "История", "Импорт"]
    )

    with tab_overview:
        _tab_overview(daily, scale_daily)

    with tab_program:
        _tab_program()

    with tab_log:
        _tab_log_entry()

    with tab_strength:
        _tab_strength()

    with tab_history:
        _tab_history(daily)

    with tab_import:
        _tab_import()
