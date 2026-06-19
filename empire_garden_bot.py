"""Бот продаж «Сад и огород» — lead + каталог (YooKassa позже)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

from analytics_db import init_analytics_db, log_event
from garden_links import garden_bot_link
from sales_db import SALES_DB_PATH, init_sales_db, list_products_for_persona

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("empire.garden_bot")

TOKEN = os.getenv("GARDEN_BOT_TOKEN", "").strip()
ROOT = os.path.dirname(os.path.abspath(__file__))
LEAD_JSON = os.path.join(ROOT, "data", "garden_lead.json")
PRODUCTS_JSON = os.path.join(ROOT, "data", "garden_products.json")

DISCLAIMER_TEXT = (
    "<b>⚠️ Перед советами</b>\n\n"
    "Материалы бота — обзор приёмов природного огородничества для любителей. "
    "Это <b>не</b> агрономическое сопровождение и не замена очному осмотру участка.\n\n"
    "Учитывайте свой климат, почву и сорта. При сомнениях — местный агроном или садовое товарищество."
)

WAITLIST_TEXT = (
    "Оплата PDF откроется после финальной вычитки материалов. "
    "Вы в листе ожидания — напишем в этом боте.\n\n"
    "Пока — бесплатные советы в канале и lead выше."
)


def _parse_start(text: str | None) -> str | None:
    if not text:
        return None
    m = re.match(r"/start(?:\s+)?(.+)", text.strip())
    return m.group(1).strip() if m else None


def _db() -> sqlite3.Connection:
    init_sales_db()
    conn = sqlite3.connect(SALES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _upsert_user(tg_id: int, username: str | None, source_id: str | None) -> None:
    conn = _db()
    conn.execute(
        "INSERT INTO course_users (tg_id, username, source_id) VALUES (?,?,?) "
        "ON CONFLICT(tg_id) DO UPDATE SET username=excluded.username, "
        "source_id=COALESCE(excluded.source_id, course_users.source_id)",
        (tg_id, username, source_id),
    )
    conn.commit()
    conn.close()


def _load_lead() -> tuple[str, str]:
    if os.path.isfile(LEAD_JSON):
        data = json.loads(open(LEAD_JSON, encoding="utf-8").read())
        return data.get("title", "🌱 Советы"), data.get("body", "")
    return "🌱 Советы", "Мульча, полив, сезон — смотрите канал."


def _product_blurb(code: str) -> str:
    if not os.path.isfile(PRODUCTS_JSON):
        return ""
    for p in json.loads(open(PRODUCTS_JSON, encoding="utf-8").read()).get("products", []):
        if p.get("code") == code:
            return p.get("description", "")
    return ""


def _disclaimer_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Понял, продолжаем", callback_data="gdisc_ok")],
            [InlineKeyboardButton(text="❌ Не сейчас", callback_data="gdisc_no")],
        ]
    )


def _catalog_kb() -> InlineKeyboardMarkup:
    prods = list_products_for_persona("garden")
    rows = []
    for p in prods:
        pay = "купить" if p.get("payments_enabled") else "скоро"
        rows.append([
            InlineKeyboardButton(
                text=f"{p['name']} — {int(p['price_rub'])} ₽ ({pay})",
                callback_data=f"buy:{p['code']}",
            )
        ])
    rows.append([InlineKeyboardButton(text="📋 Лист ожидания", callback_data="waitlist")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def cmd_start(message: types.Message):
    source_id = _parse_start(message.text)
    _upsert_user(message.from_user.id, message.from_user.username, source_id)
    init_analytics_db()
    log_event("garden_bot_start", source_id=source_id, persona_key="garden", payload={"bot": "garden_sales"})
    await message.answer(DISCLAIMER_TEXT, parse_mode="HTML", reply_markup=_disclaimer_kb())


async def on_disclaimer(cb: CallbackQuery):
    if cb.data == "gdisc_ok":
        conn = _db()
        conn.execute("UPDATE course_users SET disclaimer_ok=1 WHERE tg_id=?", (cb.from_user.id,))
        conn.commit()
        conn.close()
        title, body = _load_lead()
        await cb.message.answer(f"<b>{title}</b>\n\n{body}", parse_mode="HTML")
        await cb.message.answer("Каталог материалов:", reply_markup=_catalog_kb())
        await cb.answer()
    else:
        await cb.message.answer("Ок. Загляните, когда будете готовы — /start")
        await cb.answer()


async def cmd_catalog(message: types.Message):
    await message.answer("<b>Каталог</b>", parse_mode="HTML", reply_markup=_catalog_kb())


async def on_buy(cb: CallbackQuery):
    if not cb.data or not cb.data.startswith("buy:"):
        return
    code = cb.data.split(":", 1)[1]
    prods = {p["code"]: p for p in list_products_for_persona("garden")}
    p = prods.get(code)
    if not p:
        await cb.answer("Нет в каталоге", show_alert=True)
        return
    blurb = _product_blurb(code)
    if p.get("payments_enabled"):
        await cb.message.answer("Оплата подключается. Пока — /waitlist")
    else:
        text = (
            f"<b>{p['name']}</b>\n"
            f"Цена: {int(p['price_rub'])} ₽\n\n"
            f"{blurb}\n\n"
            f"{WAITLIST_TEXT}"
        )
        await cb.message.answer(text, parse_mode="HTML")
        conn = _db()
        conn.execute(
            "INSERT INTO course_users (tg_id, username, waitlist) VALUES (?,?,1) "
            "ON CONFLICT(tg_id) DO UPDATE SET waitlist=1",
            (cb.from_user.id, cb.from_user.username),
        )
        conn.commit()
        conn.close()
        init_analytics_db()
        log_event("garden_waitlist", persona_key="garden", payload={"product": code})
    await cb.answer()


async def on_waitlist_cb(cb: CallbackQuery):
    conn = _db()
    conn.execute(
        "INSERT INTO course_users (tg_id, username, waitlist) VALUES (?,?,1) "
        "ON CONFLICT(tg_id) DO UPDATE SET waitlist=1",
        (cb.from_user.id, cb.from_user.username),
    )
    conn.commit()
    conn.close()
    init_analytics_db()
    log_event("garden_waitlist", persona_key="garden", payload={"via": "button"})
    await cb.message.answer("Записал в лист ожидания. Сообщим, когда PDF будет в продаже.")
    await cb.answer()


async def cmd_waitlist(message: types.Message):
    conn = _db()
    conn.execute(
        "INSERT INTO course_users (tg_id, username, waitlist) VALUES (?,?,1) "
        "ON CONFLICT(tg_id) DO UPDATE SET waitlist=1",
        (message.from_user.id, message.from_user.username),
    )
    conn.commit()
    conn.close()
    init_analytics_db()
    log_event("garden_waitlist", persona_key="garden", payload={"via": "command"})
    await message.answer("Вы в листе ожидания на tripwire и гайд.")


async def cmd_link(message: types.Message):
    """Ссылка для админа / теста."""
    link = garden_bot_link("manual")
    await message.answer(link or "Задайте EMPIRE_GARDEN_BOT_USERNAME в .env")


async def main():
    if not TOKEN:
        raise SystemExit("GARDEN_BOT_TOKEN не задан в .env")
    init_sales_db()
    init_analytics_db()
    bot = Bot(TOKEN)
    dp = Dispatcher()
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_catalog, Command("catalog"))
    dp.message.register(cmd_waitlist, Command("waitlist"))
    dp.message.register(cmd_link, Command("link"))
    dp.callback_query.register(on_disclaimer, F.data.in_({"gdisc_ok", "gdisc_no"}))
    dp.callback_query.register(on_buy, F.data.startswith("buy:"))
    dp.callback_query.register(on_waitlist_cb, F.data == "waitlist")
    logger.info("empire_garden_bot polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
