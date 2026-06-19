"""Донат-бот канала «Ленин»: Telegram Stars (XTR) + учёт в sales.db."""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery
from dotenv import load_dotenv

from analytics_db import init_analytics_db, log_event
from donate_links import DONATE_CAMPAIGN, alien_campaign_message, parse_start_param
from sales_db import donation_stats, load_donate_campaigns, record_donation

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("empire.donate_bot")

TOKEN = os.getenv("DONATE_BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")
STARS_TO_RUB = float(os.getenv("EMPIRE_STARS_TO_RUB", "1.8"))

WELCOME = (
    "<b>☭ Поддержка канала «Ленин»</b>\n\n"
    "Добровольный донат на хостинг, правки текстов и работу редактора.\n"
    "Оплата — <b>Telegram Stars</b> (⭐).\n\n"
    "Выберите сумму:"
)


def _lenin_campaign() -> dict:
    camps = load_donate_campaigns()
    return camps.get(DONATE_CAMPAIGN) or {
        "title": "Поддержка канала «Ленин»",
        "description": "Добровольный донат.",
        "thanks": "Спасибо за поддержку!",
        "amounts_stars": [50, 100, 250, 500],
    }


def _invoice_payload(stars: int, source_id: str | None) -> str:
    src = source_id or ""
    return f"don|{DONATE_CAMPAIGN}|{stars}|{src}"[:128]


def _parse_payload(payload: str) -> tuple[int, str | None] | None:
    parts = (payload or "").split("|")
    if len(parts) < 3 or parts[0] != "don" or parts[1] != DONATE_CAMPAIGN:
        return None
    try:
        stars = int(parts[2])
    except ValueError:
        return None
    src = parts[3] if len(parts) > 3 and parts[3] else None
    return stars, src


def _amounts_kb(source_id: str | None) -> InlineKeyboardMarkup:
    camp = _lenin_campaign()
    amounts = camp.get("amounts_stars") or [50, 100, 250, 500]
    rows = []
    row: list[InlineKeyboardButton] = []
    for n in amounts:
        cb = f"amt:{n}"
        if source_id:
            cb += f":{source_id[:24]}"
        row.append(InlineKeyboardButton(text=f"{n} ⭐", callback_data=cb))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _reply_lenin_menu(message: types.Message, source_id: str | None, extra: str = "") -> None:
    camp = _lenin_campaign()
    text = WELCOME
    if extra:
        text = f"<i>{extra}</i>\n\n{text}"
    text += f"\n\n<i>{camp.get('description', '')}</i>"
    await message.answer(text, parse_mode="HTML", reply_markup=_amounts_kb(source_id))


async def cmd_start(message: types.Message):
    raw = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else None
    campaign, source_id = parse_start_param(raw)
    init_analytics_db()
    log_event(
        "donate_bot_start",
        source_id=source_id,
        persona_key=DONATE_CAMPAIGN,
        payload={"tg_id": message.from_user.id, "start_campaign": campaign},
    )
    alien = alien_campaign_message(campaign)
    await _reply_lenin_menu(message, source_id, extra=alien or "")


async def on_amount_cb(cb: CallbackQuery):
    if not cb.data or not cb.data.startswith("amt:"):
        return
    parts = cb.data.split(":")
    try:
        stars = int(parts[1])
    except (IndexError, ValueError):
        await cb.answer("Ошибка суммы", show_alert=True)
        return
    source_id = parts[2] if len(parts) > 2 else None
    camp = _lenin_campaign()
    await cb.bot.send_invoice(
        chat_id=cb.message.chat.id,
        title=camp.get("title", "Поддержка «Ленин»")[:32],
        description=(camp.get("description") or "Донат каналу")[:255],
        payload=_invoice_payload(stars, source_id),
        currency="XTR",
        prices=[LabeledPrice(label=f"{stars} Stars", amount=stars)],
        provider_token="",
    )
    await cb.answer()


async def pre_checkout(query: PreCheckoutQuery):
    parsed = _parse_payload(query.invoice_payload)
    if not parsed:
        await query.answer(ok=False, error_message="Некорректный платёж")
        return
    stars, _ = parsed
    if query.total_amount != stars:
        await query.answer(ok=False, error_message="Сумма не совпадает")
        return
    await query.answer(ok=True)


async def successful_payment(message: types.Message):
    sp = message.successful_payment
    if not sp:
        return
    parsed = _parse_payload(sp.invoice_payload)
    if not parsed:
        logger.warning("donation payload parse fail: %s", sp.invoice_payload)
        return
    stars, source_id = parsed
    rub_est = round(stars * STARS_TO_RUB, 2)
    row_id = record_donation(
        tg_user_id=message.from_user.id,
        username=message.from_user.username,
        campaign_code=DONATE_CAMPAIGN,
        amount_stars=stars,
        amount_rub=rub_est,
        currency=sp.currency,
        payment_method="telegram_stars",
        telegram_payment_charge_id=sp.telegram_payment_charge_id,
        invoice_payload=sp.invoice_payload,
        source_id=source_id,
    )
    init_analytics_db()
    log_event(
        "donation_paid",
        source_id=source_id,
        persona_key=DONATE_CAMPAIGN,
        payload={"donation_id": row_id, "stars": stars, "rub_est": rub_est},
    )
    thanks = _lenin_campaign().get("thanks", "Спасибо!")
    await message.answer(f"✅ {thanks}\n\nПолучено: <b>{stars} ⭐</b>", parse_mode="HTML")


async def cmd_stats(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return
    s = donation_stats(campaign_code=DONATE_CAMPAIGN, days=30)
    await message.answer(
        f"<b>Донаты «Ленин» (30 дней)</b>\n"
        f"Платежей: {s['count']}\n"
        f"Stars: {s['stars_total']} ⭐\n"
        f"Оценка ₽ (×{STARS_TO_RUB}): {s['rub_total']:.0f}",
        parse_mode="HTML",
    )


async def main():
    if not TOKEN:
        raise SystemExit("DONATE_BOT_TOKEN не задан в .env")
    init_analytics_db()
    bot = Bot(TOKEN)
    dp = Dispatcher()
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(successful_payment, F.successful_payment)
    dp.pre_checkout_query.register(pre_checkout)
    dp.callback_query.register(on_amount_cb, F.data.startswith("amt:"))
    logger.info("empire_donate_bot polling (Lenin / Stars only)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
