# PDF -> MP3 Telegram Bot

Этот бот принимает PDF в Telegram, извлекает текст, чистит его для озвучки, генерирует качественный русский TTS через Gemini и отправляет обратно `mp3`.

## Что умеет

- принимает PDF от `ADMIN_ID`
- извлекает текст через `PyMuPDF`
- чистит текст для нормального звучания
- озвучивает длинные документы по кускам
- большие книги автоматически отправляет несколькими `mp3`-частями

## Переменные окружения

Нужны в корневом `.env` проекта:

```env
PDF_AUDIO_BOT_TOKEN=        # отдельный токен именно для этого бота
PDF_AUDIO_PIPELINE=v1       # v2 = ru_tts (SSML + optional Whisper QA)
PDF_AUDIO_QA=0              # 1 только с pipeline=v2 и faster-whisper
PDF_AUDIO_WHISPER_MODEL=small
ADMIN_ID=                   # твой Telegram user id
GEMINI_API_KEY=             # ключ Google AI Studio / Gemini

# необязательно
PDF_AUDIO_TTS_MODEL=gemini-2.5-flash-preview-tts
PDF_AUDIO_TTS_VOICE=charon
PDF_AUDIO_MAX_PDF_MB=20
PDF_AUDIO_PART_TARGET_CHARS=18000
PDF_AUDIO_CHUNK_MAX_CHARS=2500
PDF_AUDIO_RETRIES=3
```

Если `PDF_AUDIO_BOT_TOKEN` не задан, бот попытается использовать обычный `TELEGRAM_TOKEN`, но лучше выдать отдельный токен.

## Установка

```bash
cd /root/projects/empire
./venv/bin/pip install -r bots/stepanich/requirements-pdf-audio.txt
sudo apt-get update
sudo apt-get install -y ffmpeg
```

## Запуск

```bash
cd /root/projects/empire
./venv/bin/python bots/stepanich/pdf_audio_bot.py
```

## Как пользоваться

1. Открой бота в Telegram.
2. Пришли PDF-файл документом.
3. Дождись обработки.
4. Получи один или несколько `mp3` обратно.

## Примечания

- Бот сейчас закрыт для всех, кроме `ADMIN_ID`.
- Для очень больших PDF проще держать этого бота под отдельным токеном и отдельным `systemd`-сервисом.
- Если захочешь еще выше качество голоса, следующим шагом можно переключить TTS-провайдер на ElevenLabs.
