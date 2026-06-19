# Voice pipeline · простой режим (без Google на VPS)

**Google OAuth на сервере больше не нужен.**

## На ПК (один раз, ~5 мин)

1. [Google Drive для Windows](https://www.google.com/drive/download/) — папка `G:\Мой диск\Easy Voice Recorder`
2. PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File "F:\YandexDisk\obsidian (2)\Life\tools\install_voice_sync_task.ps1"
```

Готово. Каждые 15 мин записи копируются в `Life\voice\raw` на Яндекс.Диске.

## VPS

Уже: `VOICE_SOURCE=yandex`, таймер 15 мин, Whisper, маршруты.

## Проверка

1. Запись на телефон → подождать синк Google (2–3 мин)
2. Через 15–30 мин — заметка в Obsidian (или `sudo systemctl start voice-pipeline.service` на VPS)

Подробно: `docs/voice_simple_ru.md`
