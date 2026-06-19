"""Вкладка «Портфель» — роутер между Snowball UI и классическим интерфейсом."""

from __future__ import annotations

from portfolio.db import db_session, get_setting, init_db


def page_portfolio():
    with db_session() as conn:
        init_db(conn)
        mode = get_setting(conn, "portfolio_ui_mode", "snowball")

    if mode == "classic":
        from portfolio.dashboard_page_classic import page_portfolio_classic

        page_portfolio_classic()
    else:
        from portfolio.ui.snowball import page_portfolio_snowball

        page_portfolio_snowball()
