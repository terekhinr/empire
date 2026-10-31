"""Пароль дашборда внутри Streamlit (nginx basic auth ломает JS/WebSocket)."""

from __future__ import annotations

import streamlit as st

from portfolio.auth import expected_password, password_matches

_matches = password_matches


def require_dashboard_login() -> None:
    expected = expected_password()
    if not expected:
        st.error("Пароль дашборда не задан (EMPIRE_DASHBOARD_PASSWORD).")
        st.stop()
    if st.session_state.get("empire_dash_ok"):
        return
    st.title("Око Саурона")
    st.caption("Личный кабинет Empire")
    entered = st.text_input("Пароль", type="password", key="empire_dash_pw")
    if st.button("Войти", type="primary"):
        if password_matches(entered, expected):
            st.session_state.empire_dash_ok = True
            st.rerun()
        st.error("Неверный пароль")
    st.stop()
