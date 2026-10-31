"""Snowball Analytics–style portfolio UI."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from portfolio.calc.metrics import SnowballMetrics, compute_metrics, fmt_pct, fmt_rub, fmt_xirr
from portfolio.calc.snapshots import load_snapshot_history
from portfolio.config import ASSET_CLASS_LABELS, DEFAULT_CUSHION_RUB
from portfolio.dashboard_page_classic import _render_import, _render_manual
from portfolio.db import db_session, get_setting, init_db, set_setting
from portfolio.sync import refresh_prices, run_full_sync
from portfolio.ui.theme import color_class, hero_block, inject_snowball_css, kpi_card


def _kpi_row(cols, items: list[tuple[str, str, str | None, str]]):
    for col, (label, value, delta, dcls) in zip(cols, items):
        with col:
            st.markdown(kpi_card(label, value, delta, dcls), unsafe_allow_html=True)


def _render_hero(m: SnowballMetrics):
    day_pos = None
    if m.day_change_abs is not None:
        day_pos = m.day_change_abs >= 0
    st.markdown(
        hero_block(
            fmt_rub(m.total_value),
            fmt_rub(m.day_change_abs, signed=True) if m.day_change_abs is not None else "—",
            fmt_pct(m.day_change_pct) if m.day_change_pct is not None else "—",
            day_pos,
            as_of=m.price_as_of,
        ),
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<span class="sb-pill">Позиций: {m.positions_count}</span>', unsafe_allow_html=True)
    c2.markdown(f'<span class="sb-pill">С ценой: {m.priced_count}</span>', unsafe_allow_html=True)
    c3.markdown('<span class="sb-pill">MOEX · 4 брокера</span>', unsafe_allow_html=True)


def _render_primary_kpis(m: SnowballMetrics):
    st.markdown('<div class="sb-section-title">Ключевые показатели</div>', unsafe_allow_html=True)
    r1 = st.columns(5)
    profit_cls = color_class(m.profit_abs)
    _kpi_row(
        r1,
        [
            ("Вложено", fmt_rub(m.net_invested) if m.net_invested else fmt_rub(m.cost_basis), None, ""),
            (
                "Прибыль",
                fmt_rub(m.profit_abs, signed=True) if m.profit_abs else "—",
                fmt_pct(m.profit_pct) if m.profit_pct is not None else None,
                profit_cls,
            ),
            (
                "Доходность",
                fmt_pct(m.profit_pct, signed=False) if m.profit_pct is not None else "—",
                None,
                profit_cls,
            ),
            ("XIRR", fmt_xirr(m.xirr), "MWR · годовых", ""),
            (
                "TWR",
                fmt_pct(m.twr_pct, signed=True) if m.twr_pct is not None else "—",
                fmt_pct(m.twr_annual_pct, signed=True) + " год." if m.twr_annual_pct is not None else "накопленный",
                color_class(m.twr_pct),
            ),
        ],
    )


def _render_secondary_kpis(m: SnowballMetrics):
    r2 = st.columns(6)
    month_cls = color_class(m.month_change_abs)
    ytd_cls = color_class(m.ytd_change_abs)
    total_income = (m.profit_abs or 0) + m.dividends + m.coupons
    _kpi_row(
        r2,
        [
            ("Себестоимость", fmt_rub(m.cost_basis) if m.cost_basis else "—", None, ""),
            (
                "Нереализ. P&L",
                fmt_rub(m.unrealized_pnl, signed=True) if m.unrealized_pnl else "—",
                fmt_pct(m.unrealized_pnl_pct) if m.unrealized_pnl_pct is not None else None,
                color_class(m.unrealized_pnl),
            ),
            ("Дивиденды", fmt_rub(m.dividends), None, ""),
            ("Купоны", fmt_rub(m.coupons), None, ""),
            (
                "Реализ. P&L",
                fmt_rub(m.realized_pnl, signed=True) if m.realized_pnl else "—",
                None,
                color_class(m.realized_pnl),
            ),
            ("Всего доход", fmt_rub(total_income, signed=True), "прибыль + выплаты", ""),
        ],
    )
    r3 = st.columns(5)
    _kpi_row(
        r3,
        [
            (
                "За месяц",
                fmt_rub(m.month_change_abs, signed=True) if m.month_change_abs is not None else "—",
                fmt_pct(m.month_change_pct) if m.month_change_pct is not None else None,
                month_cls,
            ),
            (
                "С начала года",
                fmt_rub(m.ytd_change_abs, signed=True) if m.ytd_change_abs is not None else "—",
                fmt_pct(m.ytd_change_pct) if m.ytd_change_pct is not None else None,
                ytd_cls,
            ),
            (
                "Див. доходность",
                fmt_pct((m.dividends / m.total_value * 100), signed=False)
                if m.total_value > 0 and m.dividends
                else "—",
                "от стоимости портфеля",
                "",
            ),
            (
                "YOC",
                fmt_pct(m.yield_on_cost_pct, signed=False) if m.yield_on_cost_pct is not None else "—",
                "выплаты / себестоимость",
                "",
            ),
            ("Выплаты", fmt_rub(m.dividends + m.coupons), "дивиденды + купоны", ""),
        ],
    )


def _allocation_charts(m: SnowballMetrics):
    st.markdown('<div class="sb-section-title">Структура портфеля</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    palette = ["#0d9488", "#2563eb", "#f59e0b", "#8b5cf6", "#64748b", "#ef4444"]

    with left:
        if m.by_class:
            cdf = pd.DataFrame(m.by_class)
            fig = px.pie(
                cdf,
                names="label",
                values="value",
                hole=0.55,
                color_discrete_sequence=palette,
                category_orders={"label": [r["label"] for r in m.by_class]},
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                height=340,
                margin=dict(t=20, b=10, l=10, r=10),
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
            for row in m.by_class:
                st.caption(f"{row['label']}: {fmt_rub(row['value'])} · {row['share_pct']:.1f} %")

    with right:
        if m.by_broker:
            bdf = pd.DataFrame(m.by_broker)
            fig2 = px.pie(
                bdf,
                names="broker",
                values="value",
                hole=0.55,
                color_discrete_sequence=palette,
            )
            fig2.update_traces(textposition="inside", textinfo="percent+label")
            fig2.update_layout(
                height=340,
                margin=dict(t=20, b=10, l=10, r=10),
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig2, use_container_width=True)


def _render_cushion(rows: list[dict], cushion: float):
    liq_total = sum(r["market_value"] or 0 for r in rows if r["asset_class"] == "liquidity")
    if liq_total <= 0 and cushion <= 0:
        return
    st.markdown('<div class="sb-section-title">Финансовая подушка</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    excess = max(0, liq_total - cushion)
    shortfall = max(0, cushion - liq_total)
    c1.metric("В ликвидности", fmt_rub(liq_total))
    c2.metric("Цель", fmt_rub(cushion))
    c3.metric("Сверх цели", fmt_rub(excess))
    c4.metric("До цели", fmt_rub(shortfall) if shortfall > 0 else "0 ₽")
    if excess > 0:
        st.info(f"Сверх подушки {fmt_rub(excess)} — кандидаты на продажу при снижении ставки.")
    elif shortfall > 0:
        st.warning(f"До цели подушки не хватает {fmt_rub(shortfall)}.")


def _broker_table(m: SnowballMetrics):
    if not m.by_broker:
        return
    st.markdown('<div class="sb-section-title">По брокерам</div>', unsafe_allow_html=True)
    bdf = pd.DataFrame(m.by_broker)
    bdf.columns = ["Брокер", "Стоимость", "Доля %", "Себестоимость", "P&L", "P&L %"]
    st.dataframe(
        bdf.style.format(
            {
                "Стоимость": "{:,.0f}",
                "Доля %": "{:.1f}",
                "Себестоимость": "{:,.0f}",
                "P&L": "{:+,.0f}",
                "P&L %": "{:+.1f}",
            },
            na_rep="—",
        ),
        use_container_width=True,
        hide_index=True,
    )


def _account_table(m: SnowballMetrics):
    if not m.by_account:
        return
    st.markdown('<div class="sb-section-title">По счетам</div>', unsafe_allow_html=True)
    adf = pd.DataFrame(m.by_account)
    adf = adf[["broker", "account", "value", "share_pct", "cost", "pnl", "pnl_pct"]]
    adf.columns = ["Брокер", "Счёт", "Стоимость", "Доля %", "Себестоимость", "P&L", "P&L %"]
    st.dataframe(
        adf.style.format(
            {
                "Стоимость": "{:,.0f}",
                "Доля %": "{:.1f}",
                "Себестоимость": "{:,.0f}",
                "P&L": "{:+,.0f}",
                "P&L %": "{:+.1f}",
            },
            na_rep="—",
        ),
        use_container_width=True,
        hide_index=True,
    )


def _performance_chart(conn):
    hist = load_snapshot_history(conn)
    daily = conn.execute(
        """
        SELECT snap_date, total_value FROM daily_snapshots
        ORDER BY snap_date
        """
    ).fetchall()
    if daily:
        ddf = pd.DataFrame([dict(r) for r in daily])
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=ddf["snap_date"],
                y=ddf["total_value"],
                mode="lines",
                fill="tozeroy",
                line=dict(color="#0d9488", width=2.5),
                fillcolor="rgba(13, 148, 136, 0.15)",
                name="Портфель",
            )
        )
        fig.update_layout(
            height=360,
            margin=dict(t=10, b=30, l=10, r=10),
            xaxis_title="",
            yaxis_title="₽",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    elif hist:
        hdf = pd.DataFrame(hist)
        fig = px.area(hdf, x="month", y="total_value")
        fig.update_layout(height=360, yaxis_title="₽", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Нет истории — снимки накапливаются при ежедневном открытии вкладки.")


def _positions_dataframe(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    price_on = df["price_date"] if "price_date" in df.columns else pd.Series([None] * len(df))
    return pd.DataFrame(
        {
            "Брокер": df["broker"],
            "Счёт": df["account_label"],
            "Тикер": df["ticker"],
            "Название": df["name"],
            "Тип": df["asset_class"].map(lambda x: ASSET_CLASS_LABELS.get(x, x)),
            "Кол-во": pd.to_numeric(df["quantity"], errors="coerce"),
            "Ср. цена": pd.to_numeric(df["avg_price"], errors="coerce"),
            "Цена": pd.to_numeric(df["last_price"], errors="coerce"),
            "Цена на": price_on,
            "Стоимость": pd.to_numeric(df["market_value"], errors="coerce"),
            "Доля %": pd.to_numeric(df["share_pct"], errors="coerce"),
            "P&L ₽": pd.to_numeric(df["pnl"], errors="coerce"),
            "Доходность %": pd.to_numeric(df["pnl_pct"], errors="coerce"),
            "Сегодня %": pd.to_numeric(df["day_change_pct"], errors="coerce"),
        }
    )


def _style_positions(display: pd.DataFrame):
    def _pnl_color(series):
        return [
            "color: #16a34a" if (v is not None and pd.notna(v) and v >= 0) else "color: #dc2626"
            if (v is not None and pd.notna(v))
            else ""
            for v in series
        ]

    fmt_map = {
        "Кол-во": "{:,.2f}",
        "Ср. цена": "{:,.2f}",
        "Цена": "{:,.2f}",
        "Стоимость": "{:,.0f}",
        "Доля %": "{:.2f}",
        "P&L ₽": "{:+,.0f}",
        "Доходность %": "{:+.1f}",
        "Сегодня %": "{:+.2f}",
    }
    color_cols = [c for c in ("P&L ₽", "Доходность %", "Сегодня %") if c in display.columns]
    styled = display.style.format(
        {k: v for k, v in fmt_map.items() if k in display.columns},
        na_rep="—",
    )
    if color_cols:
        styled = styled.apply(_pnl_color, subset=color_cols)
    return styled


def _render_dashboard(m: SnowballMetrics, rows: list[dict], cushion: float, conn):
    col_a, col_b = st.columns([4, 1])
    with col_b:
        if st.button("🔄 Котировки", use_container_width=True):
            with st.spinner("MOEX…"):
                r = refresh_prices()
                st.success(f"{r['priced']}/{r['tickers']}")
                st.rerun()
        if st.button("☁️ Синхронизация", use_container_width=True):
            with st.spinner("…"):
                st.json(run_full_sync())
                st.rerun()

    _render_hero(m)
    if m.unpriced:
        shown = ", ".join(m.unpriced[:15])
        extra = f" и ещё {len(m.unpriced) - 15}" if len(m.unpriced) > 15 else ""
        st.warning(f"Нет котировки MOEX на момент анализа: {shown}{extra}")
    _render_primary_kpis(m)
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    _render_secondary_kpis(m)
    st.divider()
    _allocation_charts(m)
    _render_cushion(rows, cushion)
    st.divider()
    _account_table(m)
    _broker_table(m)


def _render_holdings(m: SnowballMetrics, rows: list[dict]):
    if not rows:
        st.info("Нет позиций.")
        return
    display = _positions_dataframe(rows)
    c1, c2, c3 = st.columns(3)
    broker_filter = c1.multiselect(
        "Брокер",
        sorted(display["Брокер"].unique()),
        default=sorted(display["Брокер"].unique()),
    )
    class_filter = c2.multiselect(
        "Тип актива",
        sorted(display["Тип"].unique()),
        default=sorted(display["Тип"].unique()),
    )
    sort_by = c3.selectbox(
        "Сортировка",
        ["Стоимость", "Доходность %", "Сегодня %", "Доля %", "Тикер"],
        index=0,
    )
    if broker_filter:
        display = display[display["Брокер"].isin(broker_filter)]
    if class_filter:
        display = display[display["Тип"].isin(class_filter)]
    asc = sort_by == "Тикер"
    display = display.sort_values(sort_by, ascending=asc, na_position="last")
    st.dataframe(
        _style_positions(display),
        use_container_width=True,
        height=560,
    )
    st.caption(
        f"Отфильтровано: {fmt_rub(display['Стоимость'].sum())} · "
        f"Портфель: {fmt_rub(m.total_value)} · "
        f"Прибыль: {fmt_rub(m.profit_abs, signed=True)}"
    )


def _render_analytics(m: SnowballMetrics, rows: list[dict], conn):
    st.markdown('<div class="sb-section-title">Динамика стоимости</div>', unsafe_allow_html=True)
    _performance_chart(conn)
    if st.button("Сохранить месячный снимок"):
        from portfolio.calc.snapshots import save_monthly_snapshot

        save_monthly_snapshot(conn)
        st.rerun()

    st.markdown('<div class="sb-section-title">Крупнейшие позиции</div>', unsafe_allow_html=True)
    top = sorted(
        [r for r in rows if r.get("market_value")],
        key=lambda x: x["market_value"],
        reverse=True,
    )[:12]
    if top:
        tdf = _positions_dataframe(top)[
            ["Тикер", "Название", "Брокер", "Стоимость", "Доля %", "Доходность %", "Сегодня %"]
        ]
        st.dataframe(_style_positions(tdf), use_container_width=True, hide_index=True)

    if m.by_class:
        st.markdown('<div class="sb-section-title">Разбивка по типам</div>', unsafe_allow_html=True)
        cdf = pd.DataFrame(m.by_class)
        cdf = cdf.rename(columns={"label": "Тип", "value": "Стоимость", "share_pct": "Доля %"})
        st.dataframe(
            cdf[["Тип", "Стоимость", "Доля %"]].style.format(
                {"Стоимость": "{:,.0f}", "Доля %": "{:.1f}"},
            ),
            use_container_width=True,
            hide_index=True,
        )


def _render_settings_snowball():
    from portfolio.config import DEFAULT_CUSHION_RUB
    from portfolio.ui.theme import UI_MODES

    with db_session() as conn:
        init_db(conn)
        cushion = float(get_setting(conn, "cushion_rub", str(DEFAULT_CUSHION_RUB)))
        ui_mode = get_setting(conn, "portfolio_ui_mode", "snowball")

    st.markdown('<div class="sb-section-title">Интерфейс</div>', unsafe_allow_html=True)
    mode = st.radio(
        "Режим отображения",
        options=list(UI_MODES.keys()),
        format_func=lambda k: UI_MODES[k],
        index=list(UI_MODES.keys()).index(ui_mode) if ui_mode in UI_MODES else 0,
        horizontal=True,
    )
    if mode != ui_mode:
        with db_session() as conn:
            init_db(conn)
            set_setting(conn, "portfolio_ui_mode", mode)
        st.rerun()

    st.caption(
        "Snowball — компактная сводка как в Snowball Analytics. "
        "Классический — прежний интерфейс Empire (полный откат)."
    )

    st.divider()
    st.markdown('<div class="sb-section-title">Подушка и справка</div>', unsafe_allow_html=True)
    new_cushion = st.number_input(
        "Несгораемая подушка (фонды ликвидности), ₽",
        min_value=1_500_000.0,
        value=max(cushion, 1_500_000.0),
        step=50_000.0,
    )
    if st.button("Сохранить настройки"):
        with db_session() as conn:
            init_db(conn)
            set_setting(conn, "cushion_rub", str(new_cushion))
        st.success("Сохранено")
        st.rerun()

    st.markdown(
        """
**Ориентир UI:** [Snowball Analytics](https://snowball-analytics.com/) — лучшие отзывы среди
IntelInvest / Snowball / BlackTerminal для сводки и метрик. Импорт брокеров — ваш DIY-контур Empire.

1. `PORTFOLIO_TBANK_TOKEN` — Т-Инвестиции API (все открытые счета)  
2. Отчёт Альфы (XLS/XLSX) — сделки и остатки  
3. Отчёт ВТБ (XLSX) — остатки и сделки  
4. ГПБ / Ньютон — HTML-отчёт или ручной ввод  
5. Пополнения — для XIRR / TWR  

Котировки: MOEX на дату анализа. Облигации — грязная цена (номинал × % + НКД).
Отдельное окно: `./venv/bin/streamlit run portfolio/app.py --server.port 8502`
        """
    )


def page_portfolio_snowball():
    inject_snowball_css()
    st.markdown(
        '<div class="sb-wrap"><span class="sb-pill">Snowball UI</span> '
        '<span class="sb-note">Альфа · Т-Банк · ВТБ · ГПБ · MOEX на момент анализа</span></div>',
        unsafe_allow_html=True,
    )

    with db_session() as conn:
        init_db(conn)
        m, rows = compute_metrics(conn)
        cushion = float(get_setting(conn, "cushion_rub", str(DEFAULT_CUSHION_RUB)))

    if not rows:
        st.info(
            "Портфель пуст. Импортируйте отчёты или добавьте позиции вручную."
        )
        tab_import, tab_manual, tab_settings = st.tabs(["Импорт", "Ручной ввод", "Настройки"])
        with tab_import:
            _render_import()
        with tab_manual:
            _render_manual()
        with tab_settings:
            _render_settings_snowball()
        return

    tab_dash, tab_hold, tab_an, tab_import, tab_manual, tab_settings = st.tabs(
        ["Сводка", "Активы", "Аналитика", "Импорт", "Ручной ввод", "Настройки"]
    )
    with tab_dash:
        with db_session() as conn:
            init_db(conn)
            _render_dashboard(m, rows, cushion, conn)
    with tab_hold:
        _render_holdings(m, rows)
    with tab_an:
        with db_session() as conn:
            init_db(conn)
            _render_analytics(m, rows, conn)
    with tab_import:
        _render_import()
    with tab_manual:
        _render_manual()
    with tab_settings:
        _render_settings_snowball()
