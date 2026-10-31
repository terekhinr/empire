"""Snowball-inspired Streamlit theme helpers."""

from __future__ import annotations

import streamlit as st

UI_MODES = {
    "snowball": "Snowball — сводка, активы, аналитика",
    "classic": "Классический (откат)",
}

SNOWBALL_CSS = """
<style>
/* Snowball-like portfolio shell */
.sb-wrap { margin-bottom: 0.5rem; }
.sb-hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 55%, #0d9488 100%);
    border-radius: 16px;
    padding: 1.35rem 1.6rem 1.1rem;
    color: #f8fafc;
    margin-bottom: 1rem;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
}
.sb-hero-label {
    font-size: 0.82rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    opacity: 0.82;
    margin-bottom: 0.15rem;
}
.sb-hero-value {
    font-size: 2.35rem;
    font-weight: 700;
    line-height: 1.15;
    margin: 0.1rem 0 0.35rem;
}
.sb-hero-sub { font-size: 1rem; opacity: 0.95; }
.sb-pos { color: #86efac; }
.sb-neg { color: #fca5a5; }
.sb-kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.85rem 1rem 0.75rem;
    min-height: 5.1rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.sb-kpi-label {
    color: #64748b;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.2rem;
}
.sb-kpi-value {
    color: #0f172a;
    font-size: 1.28rem;
    font-weight: 650;
    line-height: 1.2;
}
.sb-kpi-delta { font-size: 0.86rem; margin-top: 0.15rem; }
.sb-section-title {
    font-size: 1.05rem;
    font-weight: 650;
    color: #0f172a;
    margin: 0.4rem 0 0.75rem;
}
.sb-pill {
    display: inline-block;
    background: #ecfeff;
    color: #0f766e;
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    font-size: 0.75rem;
    margin-right: 0.35rem;
}
.sb-note {
    color: #64748b;
    font-size: 0.82rem;
    margin-top: 0.35rem;
}
[data-testid="stMetricValue"] { font-size: 1.35rem !important; }
</style>
"""


def inject_snowball_css() -> None:
    st.markdown(SNOWBALL_CSS, unsafe_allow_html=True)


def color_class(val: float | None) -> str:
    if val is None:
        return ""
    return "sb-pos" if val >= 0 else "sb-neg"


def kpi_card(label: str, value: str, delta: str | None = None, delta_class: str = "") -> str:
    delta_html = ""
    if delta:
        delta_html = f'<div class="sb-kpi-delta {delta_class}">{delta}</div>'
    return f"""
    <div class="sb-kpi-card">
        <div class="sb-kpi-label">{label}</div>
        <div class="sb-kpi-value">{value}</div>
        {delta_html}
    </div>
    """


def hero_block(
    total: str,
    day_abs: str,
    day_pct: str,
    day_pos: bool | None,
    as_of: str | None = None,
) -> str:
    if day_pos is None:
        sub = '<span class="sb-hero-sub">Изменение за день: нет вчерашних котировок</span>'
    else:
        cls = "sb-pos" if day_pos else "sb-neg"
        sub = f'<span class="sb-hero-sub {cls}">{day_abs} · {day_pct} за сегодня</span>'
    as_of_html = ""
    if as_of:
        as_of_html = f'<div class="sb-note" style="color:#cbd5e1;margin-top:0.45rem">Котировки на {as_of}</div>'
    return f"""
    <div class="sb-hero">
        <div class="sb-hero-label">Стоимость портфеля</div>
        <div class="sb-hero-value">{total}</div>
        {sub}
        {as_of_html}
    </div>
    """
