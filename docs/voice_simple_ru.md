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

## Запасной путь через ПК

Если OAuth сбросился — `Life/tools/sync_evrec_to_life.ps1` и `install_voice_sync_task.ps1` (см. старый гайд в git history).

Полный гайд OAuth: `docs/voice_pipeline_vps_ru.md`
