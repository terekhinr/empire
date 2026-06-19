"""Вкладка «Лонгриды · Дзен/VK» — превью и очередь в модерацию."""

from __future__ import annotations

import asyncio
import subprocess
import sys

import streamlit as st

import longread_empire as le


def page_longread_publish() -> None:
    st.header("📰 Лонгриды · Дзен / VK (Empire)")
    st.caption(
        "Автопост: approve в «Модерация постов» → TG + `vk_wall` + пересборка `media/rss_pension.xml` для Дзена. "
        "Канон: `data/pension/longreads/publish/` · книга v14."
    )

    col_sel, col_plat = st.columns(2)
    with col_sel:
        num = st.selectbox(
            "Выпуск",
            options=[n for n, _ in le.META],
            format_func=lambda n: f"{n} — {dict(le.META)[n]}",
        )
    with col_plat:
        platform = st.radio("Площадка (исходник md)", ["dzen", "vk"], horizontal=True)

    md_path = le.longread_md_path(num, platform)
    if not md_path.is_file():
        st.error(f"Нет файла {md_path}. Запустите: `python3 tools/build_longread_publish.py`")
        return

    if st.button("🔄 Обновить PNG и static/longreads", key="lr_sync"):
        with st.spinner("Синхронизация…"):
            try:
                subprocess.run(
                    [sys.executable, "tools/build_longread_publish.py"],
                    cwd=str(le.ROOT),
                    check=False,
                    capture_output=True,
                )
                subprocess.run(
                    [sys.executable, "tools/build_longread_preview.py"],
                    cwd=str(le.ROOT),
                    check=True,
                    capture_output=True,
                )
                le.sync_longread_images_to_static(num)
                st.success("Картинки на месте")
            except Exception as exc:
                st.warning(f"build_longread_preview: {exc}")
                le.sync_longread_images_to_static(num)

    try:
        title, html_body, raw_md = le.load_longread_html(num, platform)
    except Exception as exc:
        st.error(str(exc))
        return

    st.subheader(title)

    sk = f"html_edit_{num}_{platform}"
    if sk not in st.session_state:
        st.session_state[sk] = html_body

    tab_dzen, tab_vk, tab_rss, tab_md, tab_edit = st.tabs(
        ["Превью Дзен", "Превью VK (текст)", "RSS content:encoded", "Исходник .md", "Правка HTML"]
    )

    edited = st.session_state[sk]

    with tab_dzen:
        st.markdown(
            f'<div style="max-width:720px;font-family:Georgia,serif;line-height:1.55">'
            f"<h1>{title}</h1>{edited}</div>",
            unsafe_allow_html=True,
        )

    with tab_vk:
        vk_text = le.vk_plain_from_html(edited)
        st.text_area("Так уйдёт на стену ВК (без картинок, v1)", vk_text, height=400)
        st.caption(f"Символов: {len(vk_text)} / 4096")

    with tab_rss:
        snippet = le.dzen_rss_snippet(title, edited)
        st.code(snippet[:12000], language="html")
        st.caption("Дзен забирает из RSS после publish + dzen_rss")

    with tab_md:
        st.code(raw_md, language="markdown")

    with tab_edit:
        new_html = st.text_area("HTML тела статьи (без h1 — заголовок из topic_raw)", edited, height=420)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("💾 Применить правки к превью"):
                st.session_state[sk] = new_html
                st.rerun()
        with c2:
            if st.button("↩️ Сбросить из .md"):
                st.session_state[sk] = html_body
                st.rerun()
        with c3:
            if st.button("📥 В очередь модерации", type="primary"):
                async def _go():
                    return await le.create_longread_draft(num, platform, html_override=st.session_state[sk])

                try:
                    d_id = asyncio.run(_go())
                    st.success(
                        f"Черновик #{d_id} → вкладка «Модерация постов». Каналы: tg + vk_wall + dzen_rss"
                    )
                except Exception as exc:
                    st.error(str(exc))

    st.info(
        "**Форматы:** `text_content` в БД = **HTML** (картинки inline на neverretire.ru/static/longreads/). "
        "Дзен = RSS HTML. VK = plain text из HTML. TG = HTML."
    )
