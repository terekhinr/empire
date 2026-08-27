import asyncio
import httpx
import os
import html
from datetime import datetime
from dotenv import load_dotenv
import importlib.util
import logging
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile 

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, select

# --- 1. НАСТРОЙКИ ИЗ .env ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

os.makedirs("media", exist_ok=True)

# --- PDF AUDIO conversion module (local) ---
# Функции PDF->MP3 лежат в pdf_audio_bot.py. Подключаем модуль по пути,
# потому что папка bots/stepanich не является python-пакетом.
import sys as _sys

_PDF_AUDIO_BOT_PATH = Path(__file__).with_name("pdf_audio_bot.py")
_spec = importlib.util.spec_from_file_location("empire_pdf_audio_bot", _PDF_AUDIO_BOT_PATH)
assert _spec and _spec.loader
_pdf_audio_mod: Any = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_sys.modules["empire_pdf_audio_bot"] = _pdf_audio_mod
_spec.loader.exec_module(_pdf_audio_mod)

convert_pdf_to_mp3s = _pdf_audio_mod.convert_pdf_to_mp3s
MEDIA_ROOT = Path(_pdf_audio_mod.MEDIA_ROOT)

PDF_AUDIO_MAX_PDF_MB = int(os.getenv("PDF_AUDIO_MAX_PDF_MB", "20"))
PDF_AUDIO_KEEP_WORKDIR = os.getenv("PDF_AUDIO_KEEP_WORKDIR", "0") == "1"
pdf_audio_lock = asyncio.Lock()

# --- 2. БАЗА ДАННЫХ ---
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

class PostDraft(Base):
    __tablename__ = "post_drafts"
    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger)
    persona_key = Column(String)
    text_content = Column(Text)
    image_prompt = Column(Text, nullable=True)
    status = Column(String, default="pending") 
    created_at = Column(DateTime, default=datetime.utcnow)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✅ База данных готова.")

# --- 3. КАРТА КАНАЛОВ И ЛИЧНОСТЕЙ ---
CHANNEL_MAP = {
    -1002008085075: "garden",
    -1002136411597: "lenin",
    -1002024827297: "stern",
    -1003960332245: "gdepar"
}
PERSONA_TO_CHANNEL = {v: k for k, v in CHANNEL_MAP.items()}

PERSONAS = {
    "garden": {
        "model": "deepseek/deepseek-chat", 
        "prompt": "Ты — Степаныч, эксперт-агроном с 40-летним стажем. Канал: 'Сеем, пашем l сад и огород'. Стиль: дельный, народный. Опираешься на ГОСТы СССР."
    },
    "lenin": {
        "model": "deepseek/deepseek-chat",
        "prompt": "Ты — Владимир Ильич Ленин. Канал: 'ЛЕНИН l Жил, жив, будет жить!'. Стиль: энергичный, публицистичный, 'Товарищи!', 'Архиважно'."
    },
    "stern": {
        "model": "deepseek/deepseek-chat",
        "prompt": "Ты — Тренер Штерн, суровый наставник. Канал: 'снегири НЕ ГИРИ'. Стиль: железная дисциплина, 'локти прижми'. Никакого фитнес-гламура."
    },
    "gdepar": {
        "model": "deepseek/deepseek-chat",
        "prompt": "Вы — дуэт старых банщиков, Михалыч и Кириллыч. Канал-форум: 'Где пар?'. Стиль: мужицкий, с юмором, 'поддай парку'."
    }
}

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- 4. ФУНКЦИЯ ГЕНЕРАЦИИ ---
async def generate_draft_content(persona_key, topic):
    persona = PERSONAS.get(persona_key, PERSONAS["garden"])
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    
    system_prompt = (
        f"{persona['prompt']}\n\n"
        "Твоя задача написать пост для канала на предложенную тему. "
        "ОБЯЗАТЕЛЬНО раздели свой ответ на 2 части с помощью заголовков:\n"
        "ТЕКСТ ПОСТА:\n(тут сам пост)\n\n"
        "ПРОМПТ ДЛЯ КАРТИНКИ:\n(тут короткий промпт на английском языке для генерации картинки)"
    )
    
    data = {
        "model": persona["model"], 
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Тема поста: {topic}"}], 
        "temperature": 0.6
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data, timeout=50.0)
            raw_text = response.json()['choices'][0]['message']['content']
            
            post_text = raw_text
            image_prompt = "Промпт не сгенерирован"
            
            if "ПРОМПТ ДЛЯ КАРТИНКИ:" in raw_text:
                parts = raw_text.split("ПРОМПТ ДЛЯ КАРТИНКИ:")
                post_text = parts[0]
                image_prompt = parts[1].strip()
                
            post_text = post_text.replace("ТЕКСТ ПОСТА:", "").strip()
            return post_text, image_prompt
        except Exception as e:
            return f"Ошибка генерации: {e}", ""

async def generate_and_download_image(image_prompt: str, draft_id: int) -> str:
    if not image_prompt or image_prompt == "Промпт не сгенерирован":
        return None
    temp_image_url = f"https://picsum.photos/seed/{draft_id}/800/800"
    file_path = f"media/draft_{draft_id}.jpg"
    async with httpx.AsyncClient() as client:
        try:
            img_response = await client.get(temp_image_url)
            with open(file_path, "wb") as f:
                f.write(img_response.content)
            return file_path
        except Exception as e:
            return None

# --- 5. АДМИНКА ---
# Примечание: прод-бот — main.py (empire_main). Здесь дублируем PDF-handler
# на случай отдельного запуска stepanich.

PDF_HELP_TEXT = (
    "<b>📖 PDF → MP3</b>\n\n"
    "1) Пришли PDF <b>документом</b> (скрепка → Файл), не фото.\n"
    f"2) Лимит до <b>{PDF_AUDIO_MAX_PDF_MB} МБ</b>, нужен текстовый слой (не чистый скан).\n"
    "3) Бот почистит текст, озвучит через Gemini и вернёт MP3 (длинные книги — частями).\n"
    "4) Не дублируй файл, пока идёт обработка.\n\n"
    "Команды: /pdf · /help"
)

@dp.message(Command("start", "help", "pdf"))
async def cmd_pdf_guide(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет прав.")
        return
    await message.answer(PDF_HELP_TEXT, parse_mode="HTML")

@dp.message(Command("draft"))
async def cmd_draft(message: types.Message):
    # ПРОВЕРКА ПРАВ: Если бот ответит этим сообщением, значит ID в .env не совпадает
    if message.from_user.id != ADMIN_ID:
        await message.answer(f"⛔ У вас нет прав администратора.\nВаш ID: `{message.from_user.id}`\nПроверьте ADMIN_ID в .env файле!", parse_mode="Markdown")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("❌ Формат: /draft [персонаж] [тема]")
        return
        
    persona_key, topic = args[1], args[2]
    if persona_key not in PERSONAS:
        await message.answer("❌ Неизвестный персонаж.")
        return

    await message.answer("⏳ Нейросеть пишет текст и рисует картинку. Ждем...")
    
    draft_text, image_prompt = await generate_draft_content(persona_key, topic)
    channel_id = PERSONA_TO_CHANNEL.get(persona_key)

    async with async_session() as session:
        new_draft = PostDraft(channel_id=channel_id, persona_key=persona_key, text_content=draft_text, image_prompt=image_prompt)
        session.add(new_draft)
        await session.commit()
        draft_id = new_draft.id

    image_path = await generate_and_download_image(image_prompt, draft_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{draft_id}"),
         InlineKeyboardButton(text="🚀 Отправить", callback_data=f"send_{draft_id}")],
        [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"regen_{draft_id}_{persona_key}")]
    ])

    safe_text = html.escape(draft_text)
    safe_prompt = html.escape(image_prompt)
    admin_caption = f"📝 <b>ЧЕРНОВИК #{draft_id} ({persona_key})</b>\n\n{safe_text}\n\n🎨 <i>Промпт:</i> <code>{safe_prompt}</code>"
    
    if image_path and len(admin_caption) < 1024:
        photo = FSInputFile(image_path)
        await message.answer_photo(photo=photo, caption=admin_caption, reply_markup=keyboard, parse_mode="HTML")
    else:
        if image_path:
            await message.answer_photo(photo=FSInputFile(image_path))
        await message.answer(admin_caption, reply_markup=keyboard, parse_mode="HTML")

# --- PDF -> MP3 ---
@dp.message(F.document)
async def handle_pdf_document(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет прав для этого действия.")
        return

    document = message.document
    if not document:
        return
    if not (document.file_name or "").lower().endswith(".pdf"):
        await message.answer("Нужен именно PDF-файл. Инструкция: /pdf")
        return

    if document.file_size and document.file_size > PDF_AUDIO_MAX_PDF_MB * 1024 * 1024:
        await message.answer(
            f"PDF слишком большой для этого бота: больше {PDF_AUDIO_MAX_PDF_MB} MB.\n/pdf"
        )
        return

    if not GEMINI_API_KEY:
        await message.answer("Не задан GEMINI_API_KEY в .env (для озвучки).")
        return

    async with pdf_audio_lock:
        status = await message.answer(
            "Скачиваю PDF и готовлю озвучку. Для больших книг это может занять несколько минут.\n"
            "Не дублируй файл. Подробности: /pdf"
        )
        workdir = MEDIA_ROOT / f"{message.chat.id}_{message.message_id}_{int(datetime.utcnow().timestamp())}"
        workdir.mkdir(parents=True, exist_ok=True)
        pdf_path = workdir / (document.file_name or "input.pdf")

        try:
            await bot.download(document, destination=pdf_path)
            await status.edit_text("PDF скачан. Извлекаю текст и озвучиваю...")

            title, mp3_paths, total_chars = await asyncio.to_thread(
                convert_pdf_to_mp3s, pdf_path, workdir
            )

            await status.edit_text(
                f"Готово. Отправляю аудио.\nНазвание: {title[:200]}\nСимволов после очистки: {total_chars}"
            )

            for idx, mp3_path in enumerate(mp3_paths, start=1):
                caption = title
                if len(mp3_paths) > 1:
                    caption = f"{title}\nЧасть {idx} из {len(mp3_paths)}"
                await message.answer_audio(
                    audio=FSInputFile(mp3_path),
                    title=mp3_path.stem[:64],
                    caption=caption[:1024],
                )

            await status.edit_text("Все части отправлены. Ещё PDF? /pdf")
        except Exception as exc:
            logging.exception("PDF->MP3 failed")
            await status.edit_text(f"Ошибка обработки PDF: {exc}\n/pdf")
        finally:
            if not PDF_AUDIO_KEEP_WORKDIR:
                try:
                    import shutil as _shutil

                    _shutil.rmtree(workdir, ignore_errors=True)
                except Exception:
                    pass

# --- 6. ОБРАБОТЧИК КНОПОК ---
@dp.callback_query(F.data.startswith("approve_"))
async def process_approve(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    draft_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        result = await session.execute(select(PostDraft).where(PostDraft.id == draft_id))
        draft = result.scalar_one_or_none()
        if draft:
            draft.status = "approved"
            await session.commit()
            await callback.answer("✅ Пост одобрен и сохранен в базу!", show_alert=False)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Отправить сейчас", callback_data=f"send_{draft_id}")]
            ])
            await callback.message.edit_reply_markup(reply_markup=keyboard)

@dp.callback_query(F.data.startswith("send_"))
async def process_send(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    draft_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        result = await session.execute(select(PostDraft).where(PostDraft.id == draft_id))
        draft = result.scalar_one_or_none()
        if not draft or draft.status == "published":
            await callback.answer("Пост уже отправлен!", show_alert=True)
            return
        try:
            image_path = f"media/draft_{draft_id}.jpg"
            if os.path.exists(image_path) and len(draft.text_content) < 1024:
                await bot.send_photo(draft.channel_id, photo=FSInputFile(image_path), caption=draft.text_content)
            else:
                await bot.send_message(draft.channel_id, draft.text_content)
                
            draft.status = "published"
            await session.commit()
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.answer("🚀 Пост улетел в канал!", show_alert=True)
        except Exception as e:
            await callback.answer(f"Ошибка отправки: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("regen_"))
async def process_regenerate(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    _, draft_id, persona_key = callback.data.split("_")
    await callback.answer("Генерирую новый вариант...")
    topic = "Напиши новый пост на ту же тему, но с другими аргументами"
    new_text, new_prompt = await generate_draft_content(persona_key, topic)
    async with async_session() as session:
        result = await session.execute(select(PostDraft).where(PostDraft.id == int(draft_id)))
        draft = result.scalar_one_or_none()
        if draft:
            draft.text_content = new_text
            draft.image_prompt = new_prompt
            draft.status = "pending"
            await session.commit()
            
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{draft_id}"),
         InlineKeyboardButton(text="🚀 Отправить", callback_data=f"send_{draft_id}")],
        [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"regen_{draft_id}_{persona_key}")]
    ])
    safe_text = html.escape(new_text)
    safe_prompt = html.escape(new_prompt)
    admin_caption = f"🔄 <b>ПЕРЕГЕНЕРИРОВАНО #{draft_id} ({persona_key})</b>\n\n{safe_text}\n\n🎨 <i>Промпт:</i> <code>{safe_prompt}</code>"
    await callback.message.edit_text(admin_caption, reply_markup=keyboard, parse_mode="HTML")

# --- 7. ПАССИВНЫЙ СЛУХАЧ КАНАЛОВ ---
@dp.message()
@dp.channel_post()
async def handle_message(message: types.Message):
    if not message.text or message.text.startswith("/"): return
    persona_key = CHANNEL_MAP.get(message.chat.id)
    if not persona_key: return
    ai_text, _ = await generate_draft_content(persona_key, message.text)
    await message.answer(ai_text)

# --- 8. ЗАПУСК ---
async def main():
    print("--- ЗАПУСК СИСТЕМЫ ---")
    await init_db() 
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n--- СИСТЕМА ОСТАНОВЛЕНА ---")