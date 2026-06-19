"""Streamlit page: goals, projects, tasks, Obsidian sync, simple canvas."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard_health import MOBILE_CSS, _inject_mobile_css
from planning_db import (
    KIND_GOAL,
    KIND_PROJECT,
    KIND_TASK,
    OBSIDIAN_INBOX,
    OBSIDIAN_SYNC_OUT,
    add_goal,
    add_project,
    add_task,
    export_obsidian_sync,
    import_obsidian_inbox,
    load_goals_df,
    load_projects_df,
    load_tasks_df,
    summary_counts,
    update_canvas,
    update_task_status,
)

STATUS_LABELS = {
    "todo": "К выполнению",
    "doing": "В работе",
    "done": "Готово",
    "cancelled": "Отменено",
}


def _task_board(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Задач нет.")
        return
    today = date.today()
    df = df.copy()
    df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
    overdue = df[df["due_date"].notna() & (df["due_date"].dt.date < today)]
    today_df = df[df["due_date"].notna() & (df["due_date"].dt.date == today)]
    week_end = today + timedelta(days=7)
    week_df = df[
        df["due_date"].notna()
        & (df["due_date"].dt.date > today)
        & (df["due_date"].dt.date <= week_end)
    ]
    later = df[
        df["due_date"].isna()
        | (df["due_date"].dt.date > week_end)
    ]

    for title, part in (
        ("Просрочено", overdue),
        ("Сегодня", today_df),
        ("7 дней", week_df),
        ("Позже / без срока", later),
    ):
        with st.expander(f"{title} ({len(part)})", expanded=title in ("Сегодня", "Просрочено")):
            for _, row in part.iterrows():
                cols = st.columns([5, 2, 2, 1])
                cols[0].markdown(f"**{row['title']}**")
                if pd.notna(row.get("due_date")):
                    cols[1].caption(str(row["due_date"].date()))
                if row.get("project_title"):
                    cols[2].caption(row["project_title"])
                new_status = cols[3].selectbox(
                    " ",
                    options=["todo", "doing", "done", "cancelled"],
                    index=["todo", "doing", "done", "cancelled"].index(row["status"]),
                    key=f"task_status_{row['id']}",
                    label_visibility="collapsed",
                )
                if new_status != row["status"]:
                    update_task_status(int(row["id"]), new_status)
                    st.rerun()


def _canvas_view() -> None:
    st.subheader("Канвас: цели → проекты → задачи")
    goals = load_goals_df()
    projects = load_projects_df()
    tasks = load_tasks_df(status="todo")
    tasks_doing = load_tasks_df(status="doing")
    active_tasks = pd.concat([tasks, tasks_doing], ignore_index=True)

    if goals.empty and projects.empty and active_tasks.empty:
        st.info("Добавьте цели, проекты или задачи — здесь появится карта связей.")
        return

    nodes: list[dict] = []
    edges: list[tuple[str, str]] = []
    y_goal, y_proj, y_task = 3, 2, 1

    for _, g in goals.iterrows():
        nid = f"goal_{g['id']}"
        nodes.append({"id": nid, "label": g["title"][:40], "x": 0, "y": y_goal, "color": "#2563eb"})
    for i, (_, p) in enumerate(projects.iterrows()):
        nid = f"proj_{p['id']}"
        nodes.append({"id": nid, "label": p["title"][:40], "x": i % 5, "y": y_proj, "color": "#16a34a"})
        if pd.notna(p.get("goal_id")):
            edges.append((f"goal_{int(p['goal_id'])}", nid))
    for i, (_, t) in enumerate(active_tasks.head(30).iterrows()):
        nid = f"task_{t['id']}"
        nodes.append({"id": nid, "label": t["title"][:32], "x": i % 6, "y": y_task, "color": "#7c3aed"})
        if pd.notna(t.get("project_id")):
            edges.append((f"proj_{int(t['project_id'])}", nid))
        elif pd.notna(t.get("goal_id")):
            edges.append((f"goal_{int(t['goal_id'])}", nid))

    if not nodes:
        return

    node_df = pd.DataFrame(nodes)
    fig = go.Figure()
    for src, dst in edges:
        s = node_df[node_df["id"] == src].iloc[0]
        d = node_df[node_df["id"] == dst].iloc[0]
        fig.add_trace(
            go.Scatter(
                x=[s["x"], d["x"], None],
                y=[s["y"], d["y"], None],
                mode="lines",
                line=dict(color="#cbd5e1", width=1.5),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    fig.add_trace(
        go.Scatter(
            x=node_df["x"],
            y=node_df["y"],
            mode="markers+text",
            text=node_df["label"],
            textposition="top center",
            marker=dict(size=28, color=node_df["color"], opacity=0.85),
            hovertext=node_df["label"],
            hoverinfo="text",
            showlegend=False,
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Упрощённый канвас связей. Полные заметки — в полях ниже.")

    gdf = load_goals_df()
    if not gdf.empty:
        g = st.selectbox("Канвас-заметка для цели", gdf["id"].tolist(), format_func=lambda i: gdf.set_index("id").loc[i, "title"])
        current = gdf.set_index("id").loc[g, "canvas_md"] or ""
        note = st.text_area("Markdown заметка цели", value=current, height=120, key=f"canvas_goal_{g}")
        if st.button("Сохранить заметку цели", key=f"save_canvas_goal_{g}"):
            update_canvas("goal", int(g), note)
            st.success("Сохранено")


def page_planning() -> None:
    _inject_mobile_css()
    st.header("📋 Планирование")
    st.caption("Задачи · проекты · цели · синхронизация с Obsidian Life/tasks")

    if "planning_obsidian_imported" not in st.session_state:
        result = import_obsidian_inbox()
        st.session_state.planning_obsidian_imported = True
        if result.get("imported"):
            st.toast(f"Импортировано задач из Obsidian: {result['imported']}", icon="📥")

    counts = summary_counts()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("К выполнению", counts["tasks_todo"])
    c2.metric("В работе", counts["tasks_doing"])
    c3.metric("Готово", counts["tasks_done"])
    c4.metric("Цели", counts["goals_active"])
    c5.metric("Проекты", counts["projects_active"])

    tab_board, tab_add, tab_canvas, tab_obsidian, tab_lists = st.tabs(
        ["Доска", "Добавить", "Канвас", "Obsidian", "Списки"]
    )

    with tab_board:
        st.subheader("Активные задачи")
        open_tasks = load_tasks_df()
        open_tasks = open_tasks[open_tasks["status"].isin(["todo", "doing"])]
        _task_board(open_tasks)

    with tab_add:
        kind = st.radio("Тип", ["Задача", "Проект", "Цель"], horizontal=True)
        if kind == "Цель":
            with st.form("add_goal"):
                title = st.text_input("Цель")
                desc = st.text_area("Описание")
                has_target = st.checkbox("Указать целевую дату")
                target = st.date_input("Целевая дата", value=date.today(), disabled=not has_target)
                if st.form_submit_button("Сохранить цель", type="primary") and title.strip():
                    add_goal(title, desc, target.isoformat() if has_target else None)
                    st.success("Цель добавлена")
                    st.rerun()
        elif kind == "Проект":
            goals = load_goals_df()
            with st.form("add_project"):
                title = st.text_input("Проект")
                desc = st.text_area("Описание")
                goal_id = None
                if not goals.empty:
                    goal_id = st.selectbox(
                        "Связанная цель",
                        [None] + goals["id"].tolist(),
                        format_func=lambda x: "—" if x is None else goals.set_index("id").loc[x, "title"],
                    )
                if st.form_submit_button("Сохранить проект", type="primary") and title.strip():
                    add_project(title, goal_id, desc)
                    st.success("Проект добавлен")
                    st.rerun()
        else:
            projects = load_projects_df()
            goals = load_goals_df()
            with st.form("add_task"):
                title = st.text_input("Задача")
                has_due = st.checkbox("Указать срок")
                due = st.date_input("Срок", value=date.today(), disabled=not has_due)
                priority = st.selectbox("Приоритет", [0, 1, 2, 3], format_func=lambda x: ["обычный", "низкий", "средний", "высокий"][x])
                project_id = None
                goal_id = None
                if not projects.empty:
                    project_id = st.selectbox(
                        "Проект",
                        [None] + projects["id"].tolist(),
                        format_func=lambda x: "—" if x is None else projects.set_index("id").loc[x, "title"],
                    )
                if not goals.empty:
                    goal_id = st.selectbox(
                        "Цель",
                        [None] + goals["id"].tolist(),
                        format_func=lambda x: "—" if x is None else goals.set_index("id").loc[x, "title"],
                    )
                note = st.text_input("Заметка")
                if st.form_submit_button("Сохранить задачу", type="primary") and title.strip():
                    add_task(
                        title,
                        project_id=project_id,
                        goal_id=goal_id,
                        priority=int(priority),
                        due_date=due.isoformat() if has_due else None,
                        note=note or None,
                    )
                    st.success("Задача добавлена")
                    st.rerun()

    with tab_canvas:
        _canvas_view()

    with tab_obsidian:
        st.markdown(
            f"Источник: `{OBSIDIAN_INBOX}`  \n"
            f"Экспорт: `{OBSIDIAN_SYNC_OUT}`"
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Импорт из inbox.md", type="primary"):
                result = import_obsidian_inbox()
                st.success(result)
                st.rerun()
        with c2:
            if st.button("Экспорт в dashboard-sync.md"):
                n = export_obsidian_sync()
                st.success(f"Записано задач: {n}")

    with tab_lists:
        st.subheader("Все задачи")
        all_tasks = load_tasks_df()
        if not all_tasks.empty:
            show = all_tasks[
                ["id", "title", "status", "kind", "due_date", "priority", "project_title", "goal_title"]
            ].copy()
            show["status"] = show["status"].map(STATUS_LABELS)
            st.dataframe(show, use_container_width=True, hide_index=True)
        st.subheader("Цели")
        st.dataframe(load_goals_df(), use_container_width=True, hide_index=True)
        st.subheader("Проекты")
        st.dataframe(load_projects_df(), use_container_width=True, hide_index=True)
