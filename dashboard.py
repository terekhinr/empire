import asyncio
import subprocess

import streamlit as st
import sqlite3
import pandas as pd
import os
import requests
from dotenv import load_dotenv

from dashboard_longread import page_longread_publish
from dashboard_health import page_health
from dashboard_planning import page_planning
from dashboard_pages import (
    page_ai_insights,
    page_analytics_extra,
    page_flags,
    page_monitoring,
    page_neurocomment,
    page_obsidian_practical,
    page_pension_news,
    page_pension_summary,
    page_finance,
    page_sales,
    page_shorts,
    page_sources,
    page_spy,
)
from portfolio.dashboard_page import page_portfolio

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FAL_KEY = os.getenv("FAL_KEY")

st.set_page_config(page_title="Empire Dashboard", page_icon="👑", layout="wide")
DB_PATH = "empire.db"

# Идентификаторы каналов 
PLATFORM_TARGETS = {
    "garden": "-1002008085075",
    "lenin": "-1002136411597",
    "stern": "-1002024827297",
    "gdepar": "-1003960332245"
}

def get_db_connection():
    # WAL-режим + расширенный busy_timeout нужны для безопасной конкурентной работы
    # с ботом (main.py) и FastAPI-сервисами (web_app.py, gdepar_app.py)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def publish_to_tg(persona_key, text, img_path):
    chat_id = PLATFORM_TARGETS.get(persona_key)
    if not chat_id:
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
    
    try:
        if img_path and os.path.exists(img_path):
            if len(text) <= 1000:
                with open(img_path, 'rb') as f:
                    requests.post(url + 'sendPhoto', data={'chat_id': chat_id, 'caption': text, 'parse_mode': 'HTML'}, files={'photo': f})
            else:
                with open(img_path, 'rb') as f:
                    requests.post(url + 'sendPhoto', data={'chat_id': chat_id}, files={'photo': f})
                requests.post(url + 'sendMessage', data={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'})
        else:
            requests.post(url + 'sendMessage', data={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'})
        return True
    except Exception as e:
        st.error(f"Ошибка отправки в TG: {e}")
        return False

def regenerate_image(prompt, d_id):
    if not FAL_KEY: return None
    path = f"media/draft_{d_id}.jpg"
    try:
        res = requests.post("https://fal.run/fal-ai/flux/schnell",
            headers={"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"},
            json={"prompt": prompt, "image_size": "square_hd", "num_inference_steps": 4})
        if res.status_code == 200:
            img_url = res.json().get("images")[0].get("url")
            img_data = requests.get(img_url).content
            with open(path, "wb") as f: f.write(img_data)
            return path
    except: pass
    return None

PUBLISH_CHANNELS = [
    ("tg", "Telegram"),
    ("dzen_rss", "Дзен RSS"),
    ("vk_wall", "VK стена"),
    ("vc_ru", "VC.ru (заглушка)"),
    ("max", "MAX (заглушка)"),
]


def _default_publish_channels(persona_key: str) -> list[str]:
    from empire_publish_channels import channels_for_persona

    return channels_for_persona(persona_key)


def _systemctl_status(unit: str) -> str:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (r.stdout or r.stderr or "?").strip() or "unknown"
    except Exception as exc:
        return f"n/a ({exc})"


async def _publish_multi_async(draft_id: int, channels: list[str], text: str, img: str | None, persona: str):
    os.environ.setdefault("EMPIRE_SKIP_EMBEDDINGS", "1")
    from main import async_session, init_db
    from empire_publish import publish_draft_multi

    await init_db()
    async with async_session() as session:
        return await publish_draft_multi(
            session,
            content_id=draft_id,
            channels=channels,
            text=text,
            image_path=img,
            persona_key=persona,
        )


st.sidebar.title("👑 Око Саурона")
st.sidebar.caption(
    "Вход: `docs/dashboard_access.md` · "
    "[neverretire.ru/hub/](https://neverretire.ru/hub/) · туннель :8501"
)
section = st.sidebar.radio(
    "Раздел",
    ["Система", "Инвестиции", "Личное", "Контент и постинг"],
    index=0,
)
if section == "Система":
    menu = st.sidebar.radio(
        "Система",
        [
            "Мониторинг",
            "Стоп-переключатели",
        ],
    )
elif section == "Инвестиции":
    menu = st.sidebar.radio(
        "Инвестиции",
        [
            "Портфель",
            "P&L · Финансы",
            "Продажи",
        ],
    )
elif section == "Личное":
    menu = st.sidebar.radio(
        "Личное",
        [
            "Здоровье",
            "Планирование",
        ],
    )
else:
    menu = st.sidebar.radio(
        "Контент и постинг",
        [
            "Модерация постов",
            "Лонгриды · Дзен/VK",
            "Obsidian · практичный режим",
            "Пенсия · новости",
            "Pension · сводка",
            "Источники",
            "Разведка · Gdepar/Stern",
            "Видео · Shorts",
            "Нейрокомментинг (TG)",
            "Аналитика",
            "AI Insights",
        ],
    )

if menu == "Модерация постов":
    st.header("📝 Черновики на проверке")

    conn = get_db_connection()
    drafts = conn.execute("SELECT * FROM post_drafts WHERE status='pending' ORDER BY created_at DESC").fetchall()

    if not drafts:
        st.success("Все сгенерированные посты проверены и отправлены! Черновиков нет.")
        st.info("Посты появятся здесь, когда сработает расписание, или если вызвать команду /draft в боте.")
    else:
        for d in drafts:
            row = dict(d)
            with st.expander(
                f"[{row['persona_key'].upper()}] Пост #{row['id']} — Создан: {row['created_at'][:16]}",
                expanded=True,
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    topic_raw = row.get("topic_raw") or ""
                    text_content = row.get("text_content") or ""
                    is_longread = topic_raw.startswith("longread-")
                    is_html = "<h2" in text_content or "<p>" in text_content
                    if is_longread or (row["persona_key"] == "pension" and is_html):
                        lr_title = topic_raw.split("|", 1)[-1] if "|" in topic_raw else f"Пост #{row['id']}"
                        tab_prev, tab_html, tab_vk = st.tabs(["Превью", "HTML", "VK текст"])
                        with tab_prev:
                            st.markdown(
                                f'<div style="max-width:720px;font-family:Georgia,serif;line-height:1.55">'
                                f"<h1>{lr_title}</h1>{text_content}</div>",
                                unsafe_allow_html=True,
                            )
                        with tab_vk:
                            from empire_publish import _strip_html_for_vk
                            st.text_area("VK", _strip_html_for_vk(text_content), height=200, disabled=True)
                        with tab_html:
                            new_text = st.text_area(
                                "HTML (редактировать):",
                                value=text_content,
                                height=350,
                                key=f"text_{row['id']}",
                            )
                    else:
                        new_text = st.text_area(
                            "Текст поста (можно редактировать):",
                            value=text_content,
                            height=250,
                            key=f"text_{row['id']}",
                        )
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("💾 Сохранить", key=f"save_{row['id']}", use_container_width=True):
                            conn.execute("UPDATE post_drafts SET text_content=? WHERE id=?", (new_text, row["id"]))
                            conn.commit()
                            conn.close() # Обязательно закрываем БД ДО рестарта страницы
                            st.success("Сохранено!")
                            st.rerun()
                    with c2:
                        ch_labels = {k: lbl for k, lbl in PUBLISH_CHANNELS}
                        default_ch = _default_publish_channels(row["persona_key"])
                        picked = st.multiselect(
                            "Каналы",
                            options=[k for k, _ in PUBLISH_CHANNELS],
                            default=default_ch,
                            format_func=lambda k: ch_labels.get(k, k),
                            key=f"ch_{row['id']}",
                        )
                        if st.button("🚀 Опубликовать", key=f"pub_{row['id']}", type="primary", use_container_width=True):
                            conn.execute("UPDATE post_drafts SET text_content=? WHERE id=?", (new_text, row["id"]))
                            conn.commit()
                            if row["persona_key"] == "pension" and not picked:
                                st.warning("Пенсия: выберите каналы или отметьте вручную.")
                            elif not picked:
                                st.error("Выберите хотя бы один канал.")
                            else:
                                results = asyncio.run(
                                    _publish_multi_async(
                                        row["id"], picked, new_text, row.get("image_path"), row["persona_key"]
                                    )
                                )
                                ok_any = any(r.ok for r in results)
                                for r in results:
                                    if r.ok:
                                        st.success(f"{r.channel}: ok")
                                    else:
                                        st.warning(f"{r.channel}: {r.detail}")
                                if ok_any or row["persona_key"] == "pension":
                                    conn.execute("UPDATE post_drafts SET status='published' WHERE id=?", (row["id"],))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    with c3:
                        if st.button("🗑 Удалить", key=f"del_{row['id']}", use_container_width=True):
                            conn.execute("DELETE FROM post_drafts WHERE id=?", (row["id"],))
                            conn.commit()
                            conn.close()
                            st.rerun()
                            
                with col2:
                    img_path = row.get("image_path")
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, caption="Сгенерированный визуал", use_container_width=True)
                    else:
                        st.info("Картинки нет")
                        
                    if row["persona_key"] not in ["pension", "lenin"]:
                        if st.button("🔄 Перегенерировать картинку", key=f"regen_{row['id']}", use_container_width=True):
                            with st.spinner("Генерация..."):
                                new_img = regenerate_image(row["image_prompt"], row["id"])
                                if new_img:
                                    conn.execute("UPDATE post_drafts SET image_path=? WHERE id=?", (new_img, row["id"]))
                                    conn.commit()
                                    conn.close()
                                    st.rerun()
                    st.caption(f"Промпт ИИ: {row.get('image_prompt')}")
    try:
        conn.close()
    except:
        pass

elif menu == "Лонгриды · Дзен/VK":
    page_longread_publish()
elif menu == "Obsidian · практичный режим":
    page_obsidian_practical()
elif menu == "Пенсия · новости":
    page_pension_news()
elif menu == "Pension · сводка":
    page_pension_summary()
elif menu == "Источники":
    page_sources()
elif menu == "Разведка · Gdepar/Stern":
    page_spy()
elif menu == "Видео · Shorts":
    page_shorts()
elif menu == "Нейрокомментинг (TG)":
    page_neurocomment()
elif menu == "Аналитика":
    st.header("📊 Статистика")
    conn = get_db_connection()
    df = pd.read_sql_query(
        "SELECT persona_key, status, count(*) as cnt FROM post_drafts GROUP BY persona_key, status",
        conn,
    )
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.groupby("persona_key")["cnt"].sum())
    try:
        pub_df = pd.read_sql_query(
            "SELECT channel, status, COUNT(*) AS cnt FROM publications GROUP BY channel, status",
            conn,
        )
        if not pub_df.empty:
            st.dataframe(pub_df, use_container_width=True)
    except Exception:
        pass
    try:
        news_n = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
        st.metric("Новостей в news", news_n)
    except Exception:
        pass
    page_analytics_extra(conn)
    conn.close()
elif menu == "AI Insights":
    page_ai_insights()
elif menu == "P&L · Финансы":
    page_finance()
elif menu == "Портфель":
    page_portfolio()
elif menu == "Продажи":
    page_sales()
elif menu == "Мониторинг":
    page_monitoring()
elif menu == "Стоп-переключатели":
    page_flags()
elif menu == "Здоровье":
    page_health()
elif menu == "Планирование":
    page_planning()