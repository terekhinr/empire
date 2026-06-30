"""Вкладки дашборда (ТЗ FINAL §4.2) — отдельный модуль для читаемости."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys

import pandas as pd
import streamlit as st

from empire_flags import load_empire_flags, save_empire_flags
from empire_sources import deeplink_tg, generate_source_id, list_links, register_link
from metrics import build_ai_insights_stub, weekly_events_summary
from finance_ledger import (
    EXPENSE_CATEGORIES,
    EXPENSE_CATEGORY_LABELS,
    INCOME_CATEGORIES,
    append_ledger_entry,
    build_pl_monthly,
    expense_by_category,
    kpi_template_csv,
    ledger_to_csv,
    load_ledger,
    load_weekly_kpi,
    pl_to_csv,
    save_weekly_kpi_row,
    ytd_totals,
)
from sales_db import init_sales_db, npd_limit_alert
from script_factory import script_to_markdown

DB_PATH = "empire.db"
ANALYTICS_DB = "analytics.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


from dashboard_ops import OPTIONAL_BOTS, service_row

def page_sources():
    st.header("🔗 Источники трафика")
    col1, col2 = st.columns(2)
    with col1:
        persona = st.selectbox("Персона", ["garden", "gdepar", "lenin", "stern", "pension"])
        label = st.text_input("Метка кампании", value="")
    with col2:
        if st.button("Создать source_id", type="primary"):
            sid = generate_source_id(persona, label)
            register_link(sid, persona, label)
            st.success(f"source_id: `{sid}`")
            st.code(deeplink_tg(sid))
    links = list_links(50)
    if links:
        st.dataframe(pd.DataFrame(links), use_container_width=True)
    else:
        st.info("Пока нет зарегистрированных ссылок.")


def page_spy():
    st.header("🕵️ Разведка конкурентов · Gdepar / Stern")
    from spy_config import spy_live_enabled, telethon_configured, telethon_session_ready

    if not spy_live_enabled():
        st.warning(
            "Разведка **выключена**, пока нет Telethon-сессии (отдельный TG-аккаунт). "
            "Сад, Ленин, Пенсия сюда не относятся. "
            "Пенсия → вкладка «Пенсия · новости» (RSS/TG-источники, ваш approve). "
            "После `scripts/telethon_login.py` снимите **stop_spy** в флагах."
        )
        if telethon_configured() and not telethon_session_ready():
            st.info("API ID/Hash есть, файла `.session` ещё нет — выполните telethon_login.")
    st.caption(
        "Взлётевшие **посты** конкурентов (zhivayabanya, obrazpar, …) → черновик **только** для Пар/Штерн. "
        "Не копипаста: переработка угла. Авточерновики из spy отключены (экономия токенов)."
    )
    persona_tab = st.radio(
        "Персона",
        ["gdepar", "stern", "все"],
        horizontal=True,
        index=0,
    )
    conn = get_db_connection()
    try:
        q = (
            "SELECT id, persona_key, competitor, er_proxy, anomaly_score, status, "
            "substr(post_text,1,120) AS preview, created_at FROM spy_signals "
        )
        if persona_tab != "все":
            q += f" WHERE persona_key = '{persona_tab}' "
        q += " ORDER BY created_at DESC LIMIT 50"
        df = pd.read_sql_query(q, conn)
    except Exception:
        st.warning("Таблица spy_signals ещё не создана. Запустите main/worker или job spy_dry_run.")
        conn.close()
        return
    if df.empty:
        st.info("Сигналов нет. Worker: job `spy_dry_run` или дождитесь 05:10 pipeline.")
        conn.close()
        return
    st.dataframe(df, use_container_width=True)
    for _, row in df.head(10).iterrows():
        with st.expander(f"#{row['id']} [{row['persona_key']}] ER={row['er_proxy']}"):
            st.write(row.get("preview", ""))
            if st.button("В сетку автопоста (черновик)", key=f"spy_draft_{row['id']}"):
                from spy_config import can_create_spy_draft

                pk = str(row.get("persona_key", ""))
                allowed, reason = can_create_spy_draft(pk)
                if not allowed:
                    st.error(
                        "Черновик из разведки недоступен: "
                        + ("нужен Telethon (отдельный TG)" if reason == "spy_telethon_required" else reason)
                    )
                else:
                    os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")

                    async def _mk(sid=int(row["id"])):
                        from main import async_session, init_db
                        from spy_to_draft import create_draft_from_spy

                        await init_db()
                        async with async_session() as session:
                            return await create_draft_from_spy(session, sid)

                    with st.spinner("LLM + картинка…"):
                        res = asyncio.run(_mk())
                    if res.get("ok"):
                        st.success(f"Черновик #{res.get('draft_id')} — см. «Модерация постов»")
                    else:
                        st.error(res.get("error", "ошибка"))
    conn.close()


def page_shorts():
    st.header("🎬 Видео · Shorts и сценарии")
    st.caption(
        "Цель: сценарии из **взлётевшего видео** конкурентов (spy, kind=video). "
        "Сейчас каркас: stern + gdepar; pension сюда не относится."
    )
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            "SELECT id, persona_key, title, hook, duration_sec, status, trend_ref, created_at "
            "FROM shorts_scripts ORDER BY created_at DESC LIMIT 40",
            conn,
        )
    except Exception:
        st.warning("Таблица shorts_scripts не найдена.")
        conn.close()
        return
    persona_filter = st.selectbox("Фильтр персоны", ["все", "stern", "gdepar", "garden", "lenin"])
    if persona_filter != "все" and not df.empty:
        df = df[df["persona_key"] == persona_filter]
    if df.empty:
        st.info("Нет сценариев. Job `shorts_scripts` или понедельник 06:00.")
    else:
        st.dataframe(df, use_container_width=True)
    if st.button("Поставить генерацию в очередь"):
        os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")

        async def _enq():
            from main import enqueue_job, init_db

            await init_db()
            return await enqueue_job(
                "shorts_scripts",
                {"per_persona": 2, "personas": ["stern", "gdepar"]},
            )

        jid = asyncio.run(_enq())
        st.success(f"Job #{jid} в очереди")
    sel_id = st.number_input("ID сценария для Markdown", min_value=1, value=int(df.iloc[0]["id"]) if len(df) else 1)
    row = conn.execute("SELECT * FROM shorts_scripts WHERE id=?", (int(sel_id),)).fetchone()
    if row:
        md = script_to_markdown(dict(row))
        st.download_button("Скачать .md", md, file_name=f"short_{sel_id}.md")
        st.markdown(md)
    conn.close()


def page_finance():
    """P&L: ledger + sales.db, экспорт CSV, KPI недели (§ empire_business_plan_2026)."""
    from datetime import date

    st.header("📒 P&L · Финансы Empire")
    st.caption(
        "Доходы из `sales.db` (оплаты) + ручной `data/empire_finance_ledger.json`. "
        "Не дублируйте одну продажу в ledger, если она уже в sales."
    )

    init_sales_db()
    ytd = ytd_totals()
    alert = npd_limit_alert()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Расходы YTD", f"{ytd['expense_ytd_rub']:,.0f} ₽")
    c2.metric("Доход YTD (sales)", f"{ytd['income_sales_ytd_rub']:,.0f} ₽")
    c3.metric("Маржа YTD", f"{ytd['margin_ytd_rub']:,.0f} ₽")
    c4.metric("НПД", f"{alert['pct']}%", delta="алёрт" if alert["alert"] else "ок")

    st.caption("AI-инструменты YTD (из ledger)")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Cursor", f"{ytd.get('expense_cursor_ytd_rub', 0):,.0f} ₽")
    a2.metric("OpenRouter", f"{ytd.get('expense_openrouter_ytd_rub', 0):,.0f} ₽")
    a3.metric("fal.ai", f"{ytd.get('expense_fal_ytd_rub', 0):,.0f} ₽")
    a4.metric("AI всего", f"{ytd.get('expense_ai_tools_ytd_rub', 0):,.0f} ₽")

    month_key = date.today().strftime("%Y-%m")
    month_cats = expense_by_category(month=month_key)
    if month_cats:
        ai_rows = [
            {
                "категория": EXPENSE_CATEGORY_LABELS.get(k, k),
                "код": k,
                "₽/мес": round(v, 2),
            }
            for k, v in sorted(month_cats.items(), key=lambda x: -x[1])
            if v > 0
        ]
        if ai_rows:
            with st.expander(f"Расходы по категориям · {month_key}"):
                st.dataframe(pd.DataFrame(ai_rows), use_container_width=True, hide_index=True)

    pl_rows = build_pl_monthly(18)
    if pl_rows:
        st.subheader("P&L по месяцам")
        pl_df = pd.DataFrame(pl_rows)
        st.dataframe(pl_df, use_container_width=True)
        st.bar_chart(pl_df.set_index("month")[["expense_rub", "income_total_rub", "margin_rub"]])
        exp_cols = st.columns(2)
        exp_cols[0].download_button(
            "Скачать P&L CSV",
            pl_to_csv(pl_rows),
            file_name="empire_pl_monthly.csv",
            mime="text/csv",
        )
        exp_cols[1].download_button(
            "Скачать ledger CSV",
            ledger_to_csv(),
            file_name="empire_finance_ledger.csv",
            mime="text/csv",
        )
    else:
        st.info("Нет данных P&L — добавьте расход VPS или дождитесь первой оплаты в sales.db.")

    st.divider()
    st.subheader("Быстро: Cursor / OpenRouter / fal.ai")
    st.caption(
        "Суммы с кабинетов (Cursor Billing, openrouter.ai/activity, fal.ai/dashboard). "
        "Валюта USD — переведите в ₽ по курсу дня."
    )
    qb = st.columns(3)
    quick_presets = (
        ("cursor", "Cursor", "Cursor"),
        ("openrouter", "OpenRouter", "OpenRouter"),
        ("fal", "fal.ai", "fal.ai"),
    )
    for col, (cat_code, label, vendor_default) in zip(qb, quick_presets):
        with col:
            with st.form(f"quick_{cat_code}"):
                qd = st.date_input("Дата", value=date.today(), key=f"qd_{cat_code}")
                qa = st.number_input("₽", min_value=0.0, value=0.0, step=10.0, key=f"qa_{cat_code}")
                qn = st.text_input("Заметка", value="", key=f"qn_{cat_code}")
                if st.form_submit_button(f"+ {label}"):
                    if qa > 0:
                        append_ledger_entry(
                            {
                                "date": qd.isoformat(),
                                "type": "expense",
                                "category": cat_code,
                                "amount_rub": qa,
                                "vendor": vendor_default,
                                "note": qn.strip() or f"{label} за период",
                            }
                        )
                        st.success("OK")
                        st.rerun()
                    else:
                        st.warning("Укажите сумму")

    st.subheader("Добавить запись в ledger")
    with st.form("ledger_add"):
        f1, f2, f3 = st.columns(3)
        d = f1.date_input("Дата", value=date.today())
        typ = f2.selectbox("Тип", ["expense", "income"])
        cats = EXPENSE_CATEGORIES if typ == "expense" else INCOME_CATEGORIES
        cat = f3.selectbox(
            "Категория",
            cats,
            format_func=lambda c: EXPENSE_CATEGORY_LABELS.get(c, c) if typ == "expense" else c,
        )
        g1, g2 = st.columns(2)
        amount = g1.number_input("Сумма ₽", min_value=0.0, value=0.0, step=1.0)
        vendor_default = {
            "cursor": "Cursor",
            "openrouter": "OpenRouter",
            "fal": "fal.ai",
            "vps": "VPS",
        }.get(cat, "")
        vendor = g2.text_input("Контрагент / vendor", value=vendor_default)
        persona = st.selectbox(
            "Персона (опц.)",
            ["", "garden", "gdepar", "stern", "pension", "lenin", "empire"],
        )
        note = st.text_input("Примечание", value="")
        if st.form_submit_button("Сохранить", type="primary"):
            append_ledger_entry(
                {
                    "date": d.isoformat(),
                    "type": typ,
                    "category": cat,
                    "amount_rub": amount,
                    "vendor": vendor.strip() or None,
                    "persona": persona or None,
                    "note": note.strip() or None,
                }
            )
            st.success("Запись добавлена")
            st.rerun()

    entries = load_ledger()
    if entries:
        st.subheader("Журнал ledger")
        st.dataframe(pd.DataFrame(entries).sort_values("date", ascending=False), use_container_width=True)

    st.divider()
    st.subheader("KPI недели (все линии · §6.2)")
    st.caption(
        "Еженедельный ритуал: заполнить KPI → Obsidian `_reviews/` из шаблона "
        "`Empire/_templates/weekly_project_review.md` · `docs/PROJECT_OS.md` · "
        "Google Sheets: `docs/empire_kpi_sheets_template.md`."
    )
    st.download_button(
        "Шаблон KPI CSV (Google Sheets)",
        kpi_template_csv(),
        file_name="empire_weekly_kpi_template.csv",
        mime="text/csv",
    )
    with st.form("empire_weekly_kpi"):
        w = st.text_input("Неделя (ISO)", value=date.today().isoformat())
        r0 = st.columns(3)
        cur_spend = r0[0].number_input("Cursor ₽/нед", min_value=0.0, value=0.0)
        or_spend = r0[1].number_input("OpenRouter ₽/нед", min_value=0.0, value=0.0)
        fal_spend = r0[2].number_input("fal.ai ₽/нед", min_value=0.0, value=0.0)
        r1 = st.columns(4)
        empire_ok = r1[0].checkbox("Empire без сбоев", value=True)
        garden_vk = r1[1].number_input("Garden ВК subs", min_value=0, value=0)
        gdepar_sess = r1[2].number_input("Gdepar сессии", min_value=0, value=0)
        stern_leads = r1[3].number_input("Stern leads", min_value=0, value=0)
        r2 = st.columns(4)
        pen_tg = r2[0].number_input("Pension TG", min_value=0, value=0)
        pen_sess = r2[1].number_input("Pension сессии", min_value=0, value=0)
        pen_toc = r2[2].number_input("Pension /book", min_value=0, value=0)
        pen_buy = r2[3].number_input("Pension buy clicks", min_value=0, value=0)
        r2b = st.columns(4)
        tg_posts = r2b[0].number_input("TG постов/нед", min_value=0, value=0)
        ap_fail = r2b[1].number_input("Autopost failures", min_value=0, value=0)
        gift_em = r2b[2].number_input("Gift emails (−)", min_value=0, value=0)
        gd_phone = r2b[3].number_input("Gdepar phone reveals", min_value=0, value=0)
        r3 = st.columns(3)
        orders = r3[0].number_input("Заказы", min_value=0, value=0)
        rev = r3[1].number_input("Выручка ₽", min_value=0.0, value=0.0)
        exp_w = r3[2].number_input("Расходы всего ₽/нед", min_value=0.0, value=0.0)
        top_utm = st.text_input("Лучший UTM", value="")
        notes = st.text_area("Заметки", height=60)
        if st.form_submit_button("Сохранить KPI недели"):
            save_weekly_kpi_row(
                {
                    "week": w,
                    "empire_ok": 1 if empire_ok else 0,
                    "cursor_spend_rub": cur_spend,
                    "openrouter_spend_rub": or_spend,
                    "fal_spend_rub": fal_spend,
                    "garden_vk_subs": garden_vk,
                    "gdepar_sessions": gdepar_sess,
                    "stern_leads": stern_leads,
                    "pension_tg_subs": pen_tg,
                    "pension_site_sessions": pen_sess,
                    "pension_book_toc": pen_toc,
                    "pension_buy_clicks": pen_buy,
                    "tg_posts_published": tg_posts,
                    "autopost_failures": ap_fail,
                    "gift_emails": gift_em,
                    "gdepar_phone_reveals": gd_phone,
                    "orders": orders,
                    "revenue_rub": rev,
                    "expenses_rub": exp_w,
                    "top_utm": top_utm.strip(),
                    "notes": notes.strip(),
                }
            )
            st.success("OK")
            st.rerun()
    kpi_rows = load_weekly_kpi()
    if kpi_rows:
        st.dataframe(pd.DataFrame(kpi_rows), use_container_width=True)
    else:
        st.info("Пока нет строк KPI — заполните форму или импортируйте CSV в data/empire_weekly_kpi.json вручную.")

    st.caption("Док: docs/empire_business_plan_2026.md §4–7")


def page_sales():
    st.header("💰 Продажи (каркас)")
    init_sales_db()
    alert = npd_limit_alert()
    st.metric("Выручка YTD (₽)", f"{alert['revenue_ytd_rub']:,.0f}")
    st.metric("Лимит НПД", f"{alert['pct']}%", delta="алёрт" if alert["alert"] else "ок")
    if load_empire_flags().get("stop_sales"):
        st.warning("Стоп продаж включён в флагах.")
    try:
        from sales_db import list_products

        prods = list_products()
        if prods:
            st.subheader("Каталог stern")
            st.dataframe(pd.DataFrame(prods), use_container_width=True)
    except Exception as exc:
        st.caption(f"Каталог: {exc}")
    st.caption("YooKassa / pay.neverretire.ru — фаза 4.0, после ключей и съёмки уроков.")


def page_ai_insights():
    st.header("🧠 AI Insights (каркас)")
    from pathlib import Path

    insight_dir = Path("data/insights")
    if insight_dir.is_dir():
        files = sorted(insight_dir.glob("insights_*.json"), reverse=True)
        if files:
            st.caption(f"Последний файл: `{files[0].name}`")
            try:
                st.json(json.loads(files[0].read_text(encoding="utf-8")))
            except Exception:
                pass
    summary = weekly_events_summary()
    insights = build_ai_insights_stub()
    st.subheader("События за 7 дней")
    st.json(summary or {"note": "пусто"})
    st.subheader("Гипотезы (шаблон, PII очищен)")
    for h in insights.get("hypotheses", []):
        st.markdown(f"- {h}")
    if st.button("Сохранить отчёт на диск"):
        from metrics import save_weekly_insights_file

        p = save_weekly_insights_file()
        st.success(p)


def page_pension_summary():
    """Pension: сводка KPI, ссылки на кабинеты, ручной ввод метрик недели."""
    import os
    from datetime import date

    from pension_metrics import (
        latest_daily_subs,
        load_weekly_metrics,
        record_daily_subs,
        save_weekly_row,
        waitlist_count,
    )

    st.header("📘 Pension · сводка")
    st.caption("Сайт neverretire.ru · книга · метрики. Метрика и соцсети — часть данных вводится вручную раз в неделю.")

    mid = (os.getenv("YANDEX_METRIKA_ID") or "").strip()
    cols = st.columns(4)
    with cols[0]:
        if mid.isdigit():
            st.link_button(
                "Яндекс.Метрика",
                f"https://metrika.yandex.ru/dashboard?id={mid}",
                use_container_width=True,
            )
        else:
            st.caption("YANDEX_METRIKA_ID не задан")
    with cols[1]:
        yt = (
            os.getenv("PENSION_YOUTUBE_URL")
            or "https://www.youtube.com/channel/UC-XdhgaT-gXZPJpODed8Ksw"
        ).strip()
        st.link_button("YouTube Studio", yt, use_container_width=True)
    with cols[2]:
        dz = (os.getenv("PENSION_DZEN_URL") or "").strip()
        if dz:
            st.link_button("Дзен", dz, use_container_width=True)
        else:
            st.caption("PENSION_DZEN_URL — добавьте в .env")
    with cols[3]:
        vk = (os.getenv("PENSION_VK_URL") or "").strip()
        if vk:
            st.link_button("ВК", vk, use_container_width=True)
        else:
            st.caption("PENSION_VK_URL — добавьте в .env")

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Waitlist (email)", waitlist_count())
    with c2:
        try:
            import requests

            r = requests.get("http://127.0.0.1:8000/api/health", timeout=3)
            h = r.json() if r.ok else {}
            st.metric("Метрика на сайте", "да" if h.get("metrika_id_set") else "нет")
        except Exception:
            st.metric("Webapp health", "—")
    with c3:
        subs = latest_daily_subs()
        tg_s = subs.get("tg")
        st.metric("TG subs (посл. ввод)", tg_s if tg_s is not None else "—")

    st.subheader("Подписчики (ручной снимок)")
    with st.form("pension_daily_subs"):
        dcol = st.columns(4)
        tg_v = dcol[0].number_input("Telegram", min_value=0, value=0, step=1)
        vk_v = dcol[1].number_input("ВК", min_value=0, value=0, step=1)
        dz_v = dcol[2].number_input("Дзен", min_value=0, value=0, step=1)
        yt_v = dcol[3].number_input("YouTube", min_value=0, value=0, step=1)
        if st.form_submit_button("Сохранить в analytics.db"):
            record_daily_subs(
                tg=tg_v or None,
                vk=vk_v or None,
                dzen=dz_v or None,
                youtube=yt_v or None,
            )
            st.success("Сохранено")
            st.rerun()
    if subs:
        st.json(subs)

    st.subheader("Метрики недели (ручная таблица)")
    week_default = date.today().isoformat()
    with st.form("pension_weekly"):
        w = st.text_input("Неделя (ISO date)", value=week_default)
        m1, m2, m3 = st.columns(3)
        site_sessions = m1.number_input("Сессии сайта (Метрика)", min_value=0, value=0)
        book_toc = m2.number_input("Визиты /book", min_value=0, value=0)
        buy_clicks = m3.number_input("Цель buy/cta", min_value=0, value=0)
        n1, n2, n3 = st.columns(3)
        orders = n1.number_input("Заказы", min_value=0, value=0)
        revenue = n2.number_input("Выручка ₽", min_value=0, value=0)
        top_utm = n3.text_input("Лучший utm_source", value="")
        notes = st.text_area("Заметки", height=68)
        if st.form_submit_button("Записать неделю"):
            save_weekly_row(
                {
                    "week": w,
                    "site_sessions": site_sessions,
                    "book_toc": book_toc,
                    "buy_clicks": buy_clicks,
                    "orders": orders,
                    "revenue_rub": revenue,
                    "top_utm": top_utm.strip(),
                    "notes": notes.strip(),
                }
            )
            st.success("OK")
            st.rerun()

    rows = load_weekly_metrics()
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("Пока нет строк — заполните форму выше после первой недели.")

    st.subheader("События Pension (7 дней)")
    if os.path.isfile(ANALYTICS_DB):
        ac = sqlite3.connect(ANALYTICS_DB)
        try:
            ev = pd.read_sql_query(
                "SELECT event_type, COUNT(*) AS cnt FROM events "
                "WHERE persona_key='pension' AND created_at >= datetime('now', '-7 days') "
                "GROUP BY event_type ORDER BY cnt DESC",
                ac,
            )
            if not ev.empty:
                st.dataframe(ev, use_container_width=True)
            pen_all = pd.read_sql_query(
                "SELECT event_type, COUNT(*) AS cnt FROM events "
                "WHERE event_type LIKE 'pension%' "
                "AND created_at >= datetime('now', '-7 days') "
                "GROUP BY event_type ORDER BY cnt DESC",
                ac,
            )
            if not pen_all.empty and (ev.empty or len(pen_all) > len(ev)):
                st.caption("Все pension_* события")
                st.dataframe(pen_all, use_container_width=True)
        except Exception as exc:
            st.caption(str(exc))
        ac.close()

    st.caption("Док: docs/pension_analytics_accounts_guide.md · цели Метрики — создать в кабинете после YANDEX_METRIKA_ID")


def page_analytics_extra(conn):
    st.subheader("События analytics.db")
    if os.path.isfile(ANALYTICS_DB):
        ac = sqlite3.connect(ANALYTICS_DB)
        try:
            ev = pd.read_sql_query(
                "SELECT event_type, COUNT(*) AS cnt FROM events "
                "GROUP BY event_type ORDER BY cnt DESC LIMIT 20",
                ac,
            )
            if not ev.empty:
                st.dataframe(ev, use_container_width=True)
        except Exception:
            pass
        ac.close()
    st.subheader("Нейрокомментинг (dry-run)")
    try:
        nc = pd.read_sql_query(
            "SELECT status, COUNT(*) AS cnt FROM neurocomment_plans GROUP BY status",
            conn,
        )
        if not nc.empty:
            st.dataframe(nc, use_container_width=True)
    except Exception:
        st.caption("Таблица neurocomment_plans появится после pipeline.")


def page_neurocomment():
    st.header("💬 Нейрокомментинг (dry-run)")
    st.caption(
        "Комментарии в **чужих** Telegram-каналах для охвата. "
        "Не путать с редакцией Pension и не с постами Gdepar/Stern по spy."
    )
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            "SELECT id, persona_key, channel_ref, substr(planned_text,1,80) AS text, "
            "reason, status, created_at FROM neurocomment_plans "
            "ORDER BY created_at DESC LIMIT 30",
            conn,
        )
    except Exception:
        st.warning("Таблица neurocomment_plans не найдена.")
        conn.close()
        return
    if df.empty:
        st.info("Планов нет — дождитесь spy + neurocomment job.")
    else:
        st.dataframe(df, use_container_width=True)
    conn.close()


def page_monitoring():
    st.header("⚙️ Мониторинг")
    st.caption(
        "**empire_main** — один бот на все каналы (постинг по расписанию). "
        "Боты ниже — **отдельные** @BotFather-аккаунты для лидов, PDF и донатов; "
        "без своего токена они не стартуют — это нормально."
    )

    core_units = [
        "empire_main",
        "empire_worker",
        "empire_webapp",
        "empire_dashboard",
        "empire_gdepar",
        "empire_sales",
        "empire_ha_notify",
    ]
    st.subheader("Ядро")
    cols = st.columns(4)
    for i, unit in enumerate(core_units):
        row = service_row(unit)
        cols[i % 4].metric(row["unit"], row["display"])

    st.subheader("Отдельные боты (лиды / оплата / донаты)")
    for unit, meta in OPTIONAL_BOTS.items():
        row = service_row(unit)
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric(meta["label"], row["display"])
        with col2:
            st.caption(meta["note"])
            if row["detail"]:
                st.info(row["detail"])

    try:
        stv = os.statvfs("/")
        free = (stv.f_bavail * stv.f_frsize) / (1024**3)
        total = (stv.f_blocks * stv.f_frsize) / (1024**3)
        st.metric("SSD свободно", f"{free:.1f} GB", delta=f"из {total:.1f}")
    except Exception:
        pass
    conn = get_db_connection()
    for tbl in ("news", "spy_signals", "jobs", "publications"):
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            st.write(f"**{tbl}:** {n} строк")
        except Exception:
            st.write(f"**{tbl}:** —")
    conn.close()


def page_pension_news():
    """Выбор новостей из RSS → черновик разбора [ANALYSIS] (ТЗ pension)."""
    st.header("📰 Пенсия · новости и разбор")
    st.caption(
        "По расписанию — **только лента заголовков** (без воды). "
        "Здесь: выбираете новость → задаёте **голоса** (Антонов, Марков, Кримсон, Талеб) → разбор → approve."
    )
    voices = st.multiselect(
        "Голоса разбора",
        ["Антонов", "Марков", "Кримсон", "Талеб"],
        default=["Антонов", "Кримсон"],
        help="Тон и угол; факты — из новости и базы знаний.",
    )

    conn = get_db_connection()
    cat = st.selectbox(
        "Категория",
        ["all", "finance", "politics", "lifestyle"],
        format_func=lambda x: {
            "all": "Все",
            "finance": "Финансы",
            "politics": "Политика",
            "lifestyle": "Общее",
        }.get(x, x),
    )
    limit = st.slider("Сколько строк показать", 10, 80, 40)
    q = "SELECT id, title, url, category, fetched_at FROM news"
    params: tuple = ()
    if cat != "all":
        q += " WHERE category = ?"
        params = (cat,)
    q += " ORDER BY fetched_at DESC LIMIT ?"
    params = params + (limit,)
    rows = conn.execute(q, params).fetchall()
    if not rows:
        st.warning("Таблица news пуста. Нажмите «Обновить RSS» или дождитесь worker.")
    else:
        options = {r["id"]: r for r in rows}
        picked_ids = st.multiselect(
            "Новости для разбора (1–2 шт.)",
            options=list(options.keys()),
            format_func=lambda i: f"[{options[i]['category']}] {options[i]['title'][:90]}",
            max_selections=2,
        )
        angle = st.text_input("Угол / вопрос к разбору (опционально)", placeholder="Например: что это значит для рубля?")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("📝 Создать черновик разбора", type="primary", disabled=not picked_ids):
                titles = [options[i]["title"] for i in picked_ids]
                urls = [options[i]["url"] for i in picked_ids]
                topic = "[ANALYSIS] " + " · ".join(titles)
                if voices:
                    topic += "\n\nГОЛОСА РАЗБОРА (чередовать, не копипаста): " + ", ".join(voices)
                if angle.strip():
                    topic += f"\n\nУгол редактора: {angle.strip()}"
                topic += "\n\nСсылки:\n" + "\n".join(urls)

                async def _gen():
                    os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")
                    from main import (
                        PostDraft,
                        async_session,
                        generate_draft_content,
                        generate_image,
                        init_db,
                    )

                    await init_db()
                    text, img_p = await generate_draft_content("pension", topic)
                    async with async_session() as session:
                        draft = PostDraft(
                            persona_key="pension",
                            text_content=text,
                            image_prompt=img_p or "",
                            topic_raw=topic[:500],
                            decision="pending",
                        )
                        session.add(draft)
                        await session.commit()
                        await session.refresh(draft)
                        d_id = draft.id
                    img_f = None
                    if img_p:
                        img_f = await generate_image(img_p, d_id, "pension", topic_hint=topic)
                        async with async_session() as session:
                            d = await session.get(PostDraft, d_id)
                            if d:
                                d.image_path = img_f
                                await session.commit()
                    return d_id, text

                with st.spinner("Генерация разбора…"):
                    try:
                        d_id, preview = asyncio.run(_gen())
                        st.success(f"Черновик #{d_id} создан → вкладка «Модерация постов».")
                        st.text_area("Превью", preview[:4000], height=200)
                    except Exception as exc:
                        st.error(f"Ошибка: {exc}")

        with col_b:
            if st.button("🔄 Обновить RSS сейчас"):
                async def _ingest():
                    os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")
                    from main import async_session, init_db
                    from news_rss import ingest_rss_feeds

                    await init_db()
                    async with async_session() as session:
                        return await ingest_rss_feeds(session)

                with st.spinner("Загрузка лент…"):
                    try:
                        stats = asyncio.run(_ingest())
                        st.success(f"Готово: {stats}")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    conn.close()
    st.info(
        "Голоса Antonov/Crimson: `data/pension_voice_config.json`, "
        "фрагменты в `kb_sources/pension/voice/`."
    )


def page_obsidian_practical():
    """Вариант A: как писать в Obsidian и что уйдёт в Telegram по scheduled."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import obsidian_content as oc

    st.header("📓 Obsidian · практичный режим")
    st.caption(
        "Вариант A: ваш текст из `queue/*.md` → черновик в боте → «Опубликовать». "
        "Док: `docs/obsidian_practical_guide_ru.md`"
    )

    st.subheader("Правила (коротко)")
    st.markdown(
        """
| Правило | Смысл |
|--------|--------|
| **Один файл = один пост** | Несколько текстов на разные дни — **разные** `.md` в `queue/` |
| **`scheduled`** | Пост уйдёт в бот, когда время **наступило** (МСК) |
| **`status: ready`** | Участвует в очереди; `draft` / `published` — нет |
| **После выхода** | Файл в `published/` — не импортируется снова |
| **inbox, _scenarios** | Бот **не** читает |
| **Шаблон** | Новая заметка на каждый пост; `{{date}}` подставляет Obsidian, не Empire |
        """
    )

    st.subheader("Структура vault")
    st.code(
        """Empire/
  pension/queue/     ← готово к Telegram
  pension/published/ ← архив
  pension/inbox/     ← черновики для себя
  gdepar/queue/  garden/queue/  stern/queue/  lenin/queue/
""",
        language="text",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Импорт queue сейчас", type="primary"):
            ok = oc.run_import_if_needed(force=True)
            st.success("Импорт выполнен" if ok else "Импорт пропущен или ошибка (см. логи)")
            st.rerun()
    with col_b:
        incoming = os.environ.get("OBSIDIAN_EMPIRE_INCOMING", "").strip() or str(
            oc.ROOT / "data" / "obsidian_incoming"
        )
        st.caption(f"Вход: `{incoming}`")

    now = datetime.now(ZoneInfo("Europe/Moscow"))
    queue = oc.load_queue()
    state_path = oc.STATE_PATH
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    except json.JSONDecodeError:
        state = {}
    dispatched = set(state.get("dispatched_ids") or [])

    due = oc.entries_due(now)
    st.subheader(f"Сейчас по расписанию (МСК {now.strftime('%d.%m.%Y %H:%M')})")
    if due:
        st.success(f"К выдаче в бот: **{len(due)}**")
        for e in due:
            st.write(
                f"· **{e.get('id')}** — {e.get('persona')} — "
                f"{e.get('title', '')[:60]} — scheduled {e.get('scheduled', '—')}"
            )
    else:
        st.info("Нет постов с наступившим `scheduled` и `status: ready` (или уже отправлены).")

    rows = []
    for e in queue:
        sched = e.get("scheduled") or ""
        st_status = (e.get("status") or "ready").strip().lower()
        eid = e.get("id") or ""
        rows.append(
            {
                "id": eid,
                "persona": e.get("persona"),
                "title": (e.get("title") or "")[:50],
                "scheduled": sched,
                "status": st_status,
                "в боте": "да" if eid in dispatched else "",
            }
        )
    st.subheader("Очередь импорта (JSON)")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("Очередь пуста. Проверьте rclone/OBSIDIAN_EMPIRE_INCOMING и импорт.")

    with st.expander("Пример frontmatter"):
        st.markdown(
            """```yaml
---
id: pension-news-2026-05-22
persona: pension
title: "Заголовок для Telegram"
scheduled: 2026-05-22 10:00
status: ready
---
Текст поста…
```"""
        )

    st.subheader("Команды бота")
    st.code(
        "/obsidian import — переимпорт\n"
        "/obsidian list — очередь\n"
        "/obsidian due — всё с наступившим scheduled\n"
        "/obsidian now <id> — один пост сразу",
        language="text",
    )


def page_longread_publish():
    from dashboard_longread import page_longread_publish as _page

    _page()


def page_flags():
    st.header("🛑 Стоп-переключатели")
    flags = load_empire_flags()
    stop_pub = st.checkbox("Стоп публикаций", value=flags["stop_publications"])
    stop_worker = st.checkbox("Стоп worker", value=flags["stop_worker"])
    stop_scout = st.checkbox("Стоп scout", value=flags["stop_scout"])
    stop_neuro = st.checkbox("Стоп нейрокомментинга", value=flags["stop_neurocomment"])
    stop_sales = st.checkbox("Стоп продаж", value=flags["stop_sales"])
    if st.button("Сохранить", type="primary"):
        save_empire_flags(
            {
                "stop_publications": stop_pub,
                "stop_worker": stop_worker,
                "stop_scout": stop_scout,
                "stop_neurocomment": stop_neuro,
                "stop_sales": stop_sales,
            }
        )
        st.success("Сохранено")
