"""Отдельное приложение учёта портфеля (Snowball-метрики, 4 брокера, MOEX).

Запуск:
    ./venv/bin/streamlit run portfolio/app.py --server.port 8502 --server.address 127.0.0.1

Или вкладка «Портфель» в Empire Dashboard (порт 8501).
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Портфель · Empire",
    page_icon="📈",
    layout="wide",
)

from portfolio.ui.snowball import page_portfolio_snowball  # noqa: E402

page_portfolio_snowball()
