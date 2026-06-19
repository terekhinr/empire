"""Бот «Железная спина» — lead + дисклеймер (ТЗ §4.7). Оплата — после контента и YooKassa."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sqlite3

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

from analytics_db import init_analytics_db, log_event
from sales_db import SALES_DB_PATH, init_sales_db

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("empire.stern_bot")

TOKEN = os.getenv("STERN_BOT_TOKEN", "").strip()
DISCLAIMER_TEXT = (
    "<b>⚠️ Важно перед началом</b>\n\n"
    "Материалы бота — образовательные упражнения по мобильности и осанке. "
    "Это <b>не</b> медицинская консультация.\n\n"
    "<b>Не начинайте</b>, если есть: острая боль, онемение, недавняя травма, "
    "грыжа в обострении, стеноз, высокое давление без контроля врача.\n\n"
    "При ухудшении — прекратите и обратитесь к врачу."
)

LEAD_TEXT = (
    "<b>Офисный размин — 2 минуты</b>\n\n"
    "1. Сядьте ровно, стопы на полу.\n"
    "2. Медленно поверните голову влево–вправо × 5.\n"
    "3. Потяните плечи к ушам и опустите × 8.\n"
    "4. Глубокий вдох в грудь, выдох 6 сек.\n\n"
    "Если стало легче — вы уже пилотируете «обезьяну» лучше, чем вчера."
)

WAITLIST_TEXT = (
    "<b>Офисный спецназ — 3 урока</b> (390 ₽, скоро)\n\n"
    "• Видео до 90 сек: шея, грудной отдел, поясница у стола\n"
    "• Без гири на первом шаге · план ~3 мин утром / ~5 мин в обед\n"
    "• Не замена врачу\n\n"
    "Сейчас идёт съёмка. Лист ожидания: /waitlist\n"
    "Каталог: /products"
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


def _disclaimer_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Понимаю риски, продолжаем", callback_data="disc_ok")],
            [InlineKeyboardButton(text="❌ Не подходит", callback_data="disc_no")],
        ]
    )


async def cmd_start(message: types.Message):
    source_id = _parse_start(message.text)
    _upsert_user(message.from_user.id, message.from_user.username, source_id)
    init_analytics_db()
    log_event("bot_started", source_id=source_id, persona_key="stern", payload={"bot": "iron_spine"})
    await message.answer(DISCLAIMER_TEXT, parse_mode="HTML", reply_markup=_disclaimer_kb())


async def on_disclaimer(cb: CallbackQuery):
    conn = _db()
    if cb.data == "disc_ok":
        conn.execute("UPDATE course_users SET disclaimer_ok=1 WHERE tg_id=?", (cb.from_user.id,))
        conn.commit()
        conn.close()
        await cb.message.answer(LEAD_TEXT, parse_mode="HTML")
        await cb.message.answer(WAITLIST_TEXT, parse_mode="HTML")
        await cb.answer("Принято")
    else:
        conn.close()
        await cb.message.answer("Ок. Берегите себя — без согласия с дисклеймером уроки не выдаём.")
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
    await message.answer("Вы в листе ожидания. Напишем, когда tripwire откроется.")


async def cmd_products(message: types.Message):
    from sales_db import list_products

    prods = list_products()
    if not prods:
        return await message.answer("Каталог пуст.")
    lines = ["<b>Каталог (превью)</b>"]
    for p in prods:
        pay = "✅ оплата" if p.get("payments_enabled") else "🔒 скоро"
        lines.append(f"• {p['name']} — {int(p['price_rub'])} ₽ ({pay})")
    await message.answer("\n".join(lines), parse_mode="HTML")


async def main():
    if not TOKEN:
        raise SystemExit("STERN_BOT_TOKEN не задан в .env")
    init_sales_db()
    init_analytics_db()
    bot = Bot(TOKEN)
    dp = Dispatcher()
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_waitlist, Command("waitlist"))
    dp.message.register(cmd_products, Command("products"))
    dp.callback_query.register(on_disclaimer, F.data.in_({"disc_ok", "disc_no"}))
    logger.info("empire_stern_bot polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
