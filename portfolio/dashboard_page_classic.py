"""Вкладка «Портфель» в Empire Dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from portfolio.calc.metrics import SnowballMetrics, compute_metrics, fmt_pct, fmt_rub, fmt_xirr
from portfolio.calc.snapshots import load_snapshot_history, save_monthly_snapshot
from portfolio.config import ASSET_CLASS_LABELS, DEFAULT_CUSHION_RUB, IMPORTS_DIR, TBANK_TOKEN
from portfolio.db import (
    broker_account_id,
    db_session,
    get_setting,
    init_db,
    insert_cashflow,
    set_setting,
    upsert_instrument,
    upsert_manual_position,
)
from portfolio.importers.tbank_api import sync_tbank
from portfolio.sync import import_broker_file, refresh_prices, run_full_sync


def page_portfolio_classic():
    st.header("📈 Портфель · 4 брокера")
    st.caption(
        "Т-Банк (API) · Альфа (активные покупки) · ВТБ/ГПБ (пассив/архив) · котировки MOEX · XIRR"
    )

    with db_session() as conn:
        init_db(conn)

    tab_overview, tab_positions, tab_import, tab_manual, tab_settings = st.tabs(
        ["Обзор", "Позиции", "Импорт", "Ручной ввод", "Настройки"]
    )

    with tab_overview:
        _render_overview()
    with tab_positions:
        _render_positions()
    with tab_import:
        _render_import()
    with tab_manual:
        _render_manual()
    with tab_settings:
        _render_settings()


def _load_metrics() -> tuple[SnowballMetrics, list[dict]]:
    with db_session() as conn:
        init_db(conn)
        return compute_metrics(conn)


def _load_enriched() -> tuple[list[dict], float]:
    m, rows = _load_metrics()
    return rows, m.total_value


def _render_overview():
    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("🔄 Обновить котировки", use_container_width=True):
            with st.spinner("MOEX…"):
                r = refresh_prices()
                st.success(f"Цен: {r['priced']} / {r['tickers']}")
                st.rerun()
        if st.button("☁️ Полная синхронизация", use_container_width=True):
            with st.spinner("Синхронизация…"):
                res = run_full_sync()
                st.json(res)
                st.rerun()

    with db_session() as conn:
        init_db(conn)
        m, rows = compute_metrics(conn)
        cushion = float(get_setting(conn, "cushion_rub", str(DEFAULT_CUSHION_RUB)))
        hist = load_snapshot_history(conn)

    if not rows:
        st.info(
            "Портфель пуст. Добавьте позиции вручную (ГПБ) или импортируйте отчёт Альфы / "
            "подключите Т-Банк API во вкладке «Импорт»."
        )
        return

    # --- Snowball-style hero ---
    st.markdown("### Стоимость портфеля")
    hero_l, hero_r = st.columns([2, 1])
    with hero_l:
        st.markdown(f"## {fmt_rub(m.total_value)}")
        if m.day_change_abs is not None:
            color = "green" if m.day_change_abs >= 0 else "red"
            st.markdown(
                f"<span style='color:{color};font-size:1.1rem'>"
                f"{fmt_rub(m.day_change_abs, signed=True)} · {fmt_pct(m.day_change_pct)} за сегодня"
                f"</span>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Изменение за день: нет вчерашних котировок (обновите завтра)")
    with hero_r:
        st.caption(f"Позиций: {m.positions_count} · с ценой: {m.priced_count}")

    st.divider()

    # --- Основные метрики (как Snowball) ---
    r1a, r1b, r1c, r1d = st.columns(4)
    r1a.metric("Вложено", fmt_rub(m.net_invested) if m.net_invested else fmt_rub(m.cost_basis))
    r1b.metric(
        "Прибыль",
        fmt_rub(m.profit_abs, signed=True) if m.profit_abs else "—",
        delta=fmt_pct(m.profit_pct) if m.profit_pct is not None else None,
    )
    r1c.metric(
        "Доходность",
        fmt_pct(m.profit_pct, signed=False) if m.profit_pct is not None else "—",
    )
    r1d.metric(
        "XIRR (годовых)",
        fmt_xirr(m.xirr),
        help="Точен при заполненных пополнениях (вкладка «Ручной ввод»)",
    )

    r2a, r2b, r2c, r2d = st.columns(4)
    r2a.metric("Дивиденды", fmt_rub(m.dividends))
    r2b.metric("Купоны", fmt_rub(m.coupons))
    r2c.metric(
        "За месяц",
        fmt_rub(m.month_change_abs, signed=True) if m.month_change_abs is not None else "—",
        delta=fmt_pct(m.month_change_pct) if m.month_change_pct is not None else None,
    )
    r2d.metric(
        "С начала года",
        fmt_rub(m.ytd_change_abs, signed=True) if m.ytd_change_abs is not None else "—",
        delta=fmt_pct(m.ytd_change_pct) if m.ytd_change_pct is not None else None,
    )

    r3a, r3b, r3c, r3d = st.columns(4)
    r3a.metric("Себестоимость", fmt_rub(m.cost_basis) if m.cost_basis else "—")
    r3b.metric(
        "Нереализ. P&L",
        fmt_rub(m.unrealized_pnl, signed=True) if m.unrealized_pnl else "—",
        delta=fmt_pct(m.unrealized_pnl_pct) if m.unrealized_pnl_pct is not None else None,
    )
    r3c.metric(
        "Див. доходность",
        fmt_pct((m.dividends / m.total_value * 100), signed=False) if m.total_value > 0 and m.dividends else "—",
        help="Дивиденды / текущая стоимость портфеля",
    )
    r3d.metric(
        "Всего доход",
        fmt_rub(m.profit_abs + m.dividends + m.coupons, signed=True)
        if m.profit_abs
        else fmt_rub(m.dividends + m.coupons),
        help="Прибыль + дивиденды + купоны",
    )

    # --- Структура по 4 типам активов ---
    st.markdown("#### Структура по типам активов")
    if m.by_class:
        cdf = pd.DataFrame(m.by_class)
        cols4 = st.columns(len(cdf))
        for col, row in zip(cols4, cdf.itertuples()):
            col.metric(row.label, fmt_rub(row.value), delta=f"{row.share_pct:.1f} %")
        fig2 = px.pie(
            cdf,
            names="label",
            values="value",
            hole=0.45,
            category_orders={"label": [r["label"] for r in m.by_class]},
            title="Акции · ЗПИФ · Золото · Подушка",
        )
        fig2.update_layout(height=360, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig2, use_container_width=True)

    # Подушка = только фонды ликвидности
    liq_rows = [r for r in rows if r["asset_class"] == "liquidity"]
    liq_total = sum(r["market_value"] or 0 for r in liq_rows)
    if liq_total > 0 or cushion > 0:
        st.divider()
        st.markdown("#### Финансовая подушка · фонды денежного рынка")
        c1, c2, c3 = st.columns(3)
        c1.metric("В ликвидности", fmt_rub(liq_total))
        c2.metric("Цель подушки", fmt_rub(cushion))
        excess = max(0, liq_total - cushion)
        c3.metric("Сверх подушки", fmt_rub(excess))
        if excess > 0:
            st.warning(f"Сверх подушки {fmt_rub(excess)} — кандидаты на продажу при снижении ставки.")

    st.divider()

    # --- По брокерам и счетам ---
    st.markdown("#### По счетам")
    if m.by_account:
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

    st.markdown("#### По брокерам")
    if m.by_broker:
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
        fig = px.pie(
            bdf,
            names="Брокер",
            values="Стоимость",
            hole=0.45,
            title="Структура по брокерам",
        )
        fig.update_layout(height=340, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Динамика ---
    if hist:
        st.markdown("#### Динамика стоимости")
        hdf = pd.DataFrame(hist)
        fig3 = px.area(hdf, x="month", y="total_value", title="Стоимость портфеля (месячные снимки)")
        fig3.update_layout(yaxis_title="₽", xaxis_title="", height=360)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        if st.button("Сохранить месячный снимок"):
            with db_session() as conn:
                init_db(conn)
                save_monthly_snapshot(conn)
            st.rerun()

    # --- Топ позиций ---
    st.markdown("#### Крупнейшие позиции")
    top = sorted(
        [r for r in rows if r.get("market_value")],
        key=lambda x: x["market_value"],
        reverse=True,
    )[:10]
    if top:
        tdf = pd.DataFrame(top)[
            ["ticker", "name", "broker", "market_value", "share_pct", "pnl_pct", "day_change_pct"]
        ]
        tdf.columns = ["Тикер", "Название", "Брокер", "Стоимость", "Доля %", "Доходность %", "Сегодня %"]
        st.dataframe(
            tdf.style.format(
                {
                    "Стоимость": "{:,.0f}",
                    "Доля %": "{:.2f}",
                    "Доходность %": "{:+.1f}",
                    "Сегодня %": "{:+.2f}",
                },
                na_rep="—",
            ),
            use_container_width=True,
            hide_index=True,
        )


def _render_positions():
    m, rows = _load_metrics()
    if not rows:
        st.info("Нет позиций.")
        return
    df = pd.DataFrame(rows)
    display = pd.DataFrame(
        {
            "Брокер": df["broker"],
            "Счёт": df["account_label"],
            "Тикер": df["ticker"],
            "Название": df["name"],
            "Тип": df["asset_class"].map(lambda x: ASSET_CLASS_LABELS.get(x, x)),
            "Кол-во": pd.to_numeric(df["quantity"], errors="coerce"),
            "Цена": pd.to_numeric(df["last_price"], errors="coerce"),
            "Стоимость": pd.to_numeric(df["market_value"], errors="coerce"),
            "Доля %": pd.to_numeric(df["share_pct"], errors="coerce"),
            "Ср. цена": pd.to_numeric(df["avg_price"], errors="coerce"),
            "P&L ₽": pd.to_numeric(df["pnl"], errors="coerce"),
            "Доходность %": pd.to_numeric(df["pnl_pct"], errors="coerce"),
            "Сегодня %": pd.to_numeric(df["day_change_pct"], errors="coerce"),
        }
    )
    broker_filter = st.multiselect(
        "Брокер",
        sorted(display["Брокер"].unique()),
        default=sorted(display["Брокер"].unique()),
    )
    class_filter = st.multiselect(
        "Тип актива",
        sorted(display["Тип"].unique()),
        default=sorted(display["Тип"].unique()),
    )
    sort_by = st.selectbox(
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
        display.style.format(
            {
                "Кол-во": "{:,.2f}",
                "Цена": "{:,.2f}",
                "Стоимость": "{:,.0f}",
                "Доля %": "{:.2f}",
                "Ср. цена": "{:,.2f}",
                "P&L ₽": "{:+,.0f}",
                "Доходность %": "{:+.1f}",
                "Сегодня %": "{:+.2f}",
            },
            na_rep="—",
        ),
        use_container_width=True,
        height=520,
    )
    st.caption(
        f"Итого: {fmt_rub(display['Стоимость'].sum())} · "
        f"Портфель: {fmt_rub(m.total_value)} · "
        f"Прибыль: {fmt_rub(m.profit_abs, signed=True)}"
    )


def _render_import():
    st.subheader("Т-Банк · API")
    if TBANK_TOKEN:
        st.success("Токен PORTFOLIO_TBANK_TOKEN задан.")
        if st.button("Синхронизировать Т-Банк"):
            with st.spinner("Т-Банк API…"):
                try:
                    with db_session() as conn:
                        init_db(conn)
                        res = sync_tbank(conn)
                    st.json(res)
                except Exception as exc:
                    st.error(str(exc))
    else:
        st.warning(
            "Добавьте `PORTFOLIO_TBANK_TOKEN` в `.env` (read-only токен из Т-Инвестиций → Настройки → API)."
        )

    st.divider()
    st.subheader("Альфа · брокерский отчёт XLS/XLSX")
    st.caption("lk.alfadirect.ru → Отчёты → Брокерский отчёт → Сохранить XLS")
    alfa_file = st.file_uploader("Файл Альфы", type=["xls", "xlsx"], key="alfa_upload")
    if alfa_file and st.button("Импортировать Альфу", key="alfa_btn"):
        path = _save_upload(alfa_file, "alfa")
        try:
            res = import_broker_file("alfa", path)
            st.success(
                f"Разобрано: {res['parsed']}, сделок: {res['added']}, "
                f"пополнений/выводов: {res.get('cashflows', 0)}, дублей: {res['skipped']}"
            )
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("ВТБ · брокерский отчёт XLSX")
    st.caption("Мои инвестиции → Отчёты → Брокерский отчёт → Заказать в xls")
    vtb_file = st.file_uploader("Файл ВТБ", type=["xls", "xlsx"], key="vtb_upload")
    if vtb_file and st.button("Импортировать ВТБ", key="vtb_btn"):
        path = _save_upload(vtb_file, "vtb")
        try:
            res = import_broker_file("vtb", path)
            st.success(
                f"Сделок: {res['added']}, пополнений/выводов: {res.get('cashflows', 0)}, "
                f"дублей: {res['skipped']}"
            )
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Газпромбанк · Ньютон · HTML")
    st.caption(
        "Личный кабинет Ньютон Инвестиции → Отчёты → Брокерский отчёт → Сохранить HTML "
        "(или положить файл в `data/portfolio_imports/` и запустить полную синхронизацию)."
    )
    gpb_file = st.file_uploader("Файл ГПБ", type=["html", "htm"], key="gpb_upload")
    if gpb_file and st.button("Импортировать ГПБ", key="gpb_btn"):
        path = _save_upload(gpb_file, "gpb")
        try:
            res = import_broker_file("gpb", path)
            st.success(f"Позиций обновлено: {res['positions_updated']} · отчёт {res.get('report_date', '—')}")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _save_upload(uploaded, prefix: str) -> str:
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded.name).suffix or ".xlsx"
    dest = IMPORTS_DIR / f"{prefix}_{uploaded.name}"
    dest.write_bytes(uploaded.getvalue())
    return str(dest)


def _render_manual():
    st.subheader("Ручные позиции · Газпромбанк и прочее")
    st.caption("Для архивного ГПБ: введите тикер MOEX, количество и среднюю цену покупки.")

    with db_session() as conn:
        init_db(conn)
        brokers = conn.execute("SELECT code, name FROM brokers ORDER BY id").fetchall()

    b_code = st.selectbox(
        "Брокер",
        [r["code"] for r in brokers],
        format_func=lambda c: next(r["name"] for r in brokers if r["code"] == c),
        index=[r["code"] for r in brokers].index("gpb") if any(r["code"] == "gpb" for r in brokers) else 0,
    )
    c1, c2, c3, c4 = st.columns(4)
    ticker = c1.text_input("Тикер MOEX", value="SBER").strip().upper()
    qty = c2.number_input("Количество", min_value=0.0, value=0.0, step=1.0)
    avg = c3.number_input("Ср. цена покупки", min_value=0.0, value=0.0, step=0.01)
    is_liq = st.checkbox("Фонд денежного рынка (подушка)", value=False)

    asset_keys = list(ASSET_CLASS_LABELS.keys())
    default_idx = asset_keys.index("liquidity") if is_liq else 0
    asset_class = st.selectbox(
        "Тип актива",
        asset_keys,
        index=default_idx,
        format_func=lambda k: ASSET_CLASS_LABELS[k],
    )

    if st.button("Сохранить позицию", type="primary"):
        if not ticker or qty <= 0:
            st.error("Укажите тикер и количество > 0")
        else:
            with db_session() as conn:
                init_db(conn)
                aid = broker_account_id(conn, b_code)
                iid = upsert_instrument(
                    conn,
                    ticker,
                    asset_class=asset_class,
                    is_liquidity_fund=(asset_class == "liquidity"),
                )
                upsert_manual_position(
                    conn,
                    account_id=aid,
                    instrument_id=iid,
                    quantity=qty,
                    avg_price=avg if avg > 0 else None,
                    note="manual",
                )
            st.success(f"Сохранено: {ticker} × {qty}")
            st.rerun()

    st.divider()
    st.subheader("Пополнение / вывод (для XIRR)")
    d1, d2, d3, d4 = st.columns(4)
    flow_date = d1.date_input("Дата")
    flow_amount = d2.number_input("Сумма ₽", min_value=0.0, step=1000.0)
    flow_type = d3.selectbox("Тип", ["deposit", "withdrawal"])
    flow_broker = d4.selectbox("Брокер", [r["code"] for r in brokers], key="cf_broker")
    flow_note = st.text_input("Комментарий", value="")
    if st.button("Добавить поток"):
        with db_session() as conn:
            init_db(conn)
            aid = broker_account_id(conn, flow_broker)
            insert_cashflow(
                conn,
                account_id=aid,
                flow_date=flow_date.isoformat(),
                amount=float(flow_amount),
                flow_type=flow_type,
                note=flow_note or None,
                external_id=f"manual:{flow_broker}:{flow_date}:{flow_type}:{flow_amount}",
            )
        st.success("Денежный поток добавлен")
        st.rerun()


def _render_settings():
    from portfolio.ui.theme import UI_MODES

    with db_session() as conn:
        init_db(conn)
        cushion = float(get_setting(conn, "cushion_rub", str(DEFAULT_CUSHION_RUB)))
        ui_mode = get_setting(conn, "portfolio_ui_mode", "snowball")

    st.subheader("Интерфейс")
    mode = st.radio(
        "Режим отображения",
        options=list(UI_MODES.keys()),
        format_func=lambda k: UI_MODES[k],
        index=list(UI_MODES.keys()).index(ui_mode) if ui_mode in UI_MODES else 1,
        horizontal=True,
    )
    if mode != ui_mode:
        with db_session() as conn:
            init_db(conn)
            set_setting(conn, "portfolio_ui_mode", mode)
        st.rerun()

    st.divider()
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

    st.divider()
    st.markdown(
        """
**Что нужно от вас (один раз):**

1. **`PORTFOLIO_TBANK_TOKEN`** — read-only токен Т-Инвестиций (Настройки → API для инвестиций).
2. **Брокерский отчёт Альфы** (XLS) — для истории и новых покупок.
3. **Позиции ГПБ** — тикер, количество, средняя цена (вручную на вкладке «Ручной ввод»).
4. **Пополнения счетов** — для XIRR (вкладка «Ручной ввод» или из Т-Банк API).
5. По желанию: отчёт ВТБ (XLSX), если нужна точная история дивреинвеста.

Файлы импорта сохраняются в `data/portfolio_imports/`. БД: `portfolio.db`.
        """
    )
