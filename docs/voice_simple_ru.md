# Голос: телефон → Google Drive → VPS (без ПК)

**ПК в цепочке не участвует.** Записал на телефоне → через ~15 мин заметка в Obsidian (Яндекс.Диск).

## Схема

```text
[Телефон] Easy Voice Recorder
       ↓  (авто в Google Drive)
[VPS]     rclone gdrive → Whisper → .md на Яндекс.Диск
       ↓
[ПК / телефон] Obsidian (только читает)
```

| Режим | Когда |
|-------|--------|
| **gdrive** (сейчас) | OAuth на VPS один раз — `docs/voice_gdrive_oauth_ru.md` |
| yandex (запасной) | Если gdrive недоступен — скрипт `sync_evrec_to_life.ps1` на ПК |

## Куда попадают заметки

| Скажите в начале записи | Папка в vault |
|-------------------------|---------------|
| **пенсия пост**, **канал пенсия** | `Empire/pension/inbox/` |
| **на пенсию никогда**, **книга один** | `База знаний/Книги/На-пенсию-никогда/заметки/` |
| **трупик майора**, **книга два** | `База знаний/Книги/Трупик-майора/заметки/` |
| **личное** | `Life/inbox/` |
| *(ничего)* | `Входящие/` |

Аудио: `Life/voice/transcribed/`

## Проверка на VPS

```bash
rclone lsl "gdrive:Easy Voice Recorder" | tail -5
sudo systemctl start voice-pipeline.service
journalctl -u voice-pipeline.service -n 20 --no-pager
```

Таймер: `voice-pipeline.timer` — каждые 15 мин.

## ПК (не основной путь)

`Life/tools/sync_evrec_to_life.ps1` — запасной вариант.

**Ночной бэкап на ПК (рекомендуется вместо мигания каждые 15 мин):**

```powershell
cd C:\path\to\empire
powershell -ExecutionPolicy Bypass -File scripts\install_voice_rclone_nightly_windows.ps1
```

Копирует `Easy Voice Recorder` → `Life/voice/raw` на Яндекс.Диске раз в ночь (скрытое окно). Старую задачу `Empire-Voice-Sync` удаляет.

## Качество расшифровки

| Было (ПК) | Сейчас (VPS) | Что делать |
|-----------|--------------|------------|
| `small` + GPU | раньше стоял **`tiny`** на CPU | в `/etc/empire/voice.env` → `VOICE_WHISPER_MODEL=medium` |
| локальный файл | rclone с Google Drive | норм, тот же mp3 |
| float16 | int8 | для CPU это ок при `medium` |

Проверка на VPS:

```bash
cd /root/projects/empire/scripts
./venv/bin/python voice_quality_check.py --models small,medium data/voice_vault_staging/Life/voice/transcribed/ИМЯ.mp3
```

Если оба варианта плохие при bitrate < 48 kbps — поднять качество записи в Easy Voice Recorder на телефоне.

Полный гайд OAuth: `docs/voice_pipeline_vps_ru.md`
