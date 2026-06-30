# Штерн: еженедельное комик-видео

**Статус (июнь 2026): слот на паузе.** В расписании суббота 15:00 снова `stern_technique` (клипы чемпионов с YouTube) — пока нет возможности снимать своё с гирей (спина / Modic). Пайплайн ниже оставлен на «когда починю».

**Активный слот:** суббота 15:00 MSK → `stern_technique` в `content_config.json`.

## Идея (когда спина позволит)

Своя съёмка с гирей → стилизация под грубый ч/б комикс → пост с разбором Штерна.  
Не фитнес-блогер: без неонового зала, фокус на механике и пояснице.

Отдельно от `stern_technique` (клипы чемпионов с YouTube) — тот пайплайн остаётся в `tools/stern_technique_pipeline.py`, но **не в расписании**.

## Быстрый старт

```bash
# 1. Матрица упражнений (8 шт., status=pending)
./venv/bin/python tools/stern_comic_video_pipeline.py init-matrix
./venv/bin/python tools/stern_comic_video_pipeline.py list

# 2. Снять на телефон → положить в media/stern/comic_raw/
# 3. Стилизация (ffmpeg, без звука, до 50 с)
./venv/bin/python tools/stern_comic_video_pipeline.py stylize \
  --id comic_002_swing --raw media/stern/comic_raw/swing.mp4

# 4. В субботу 15:00 Empire создаст черновик с видео (если status=ready)
```

## DomoAI / ComfyUI (опционально)

Базовый фильтр — `ffmpeg` (контуры + негатив). Для «настоящего» комикса:

1. Прогнать `media/stern/comic_clips/*.mp4` через DomoAI или ComfyUI (2D, чёрные контуры).
2. Заменить файл тем же именем.
3. Или `export STERN_COMIC_STYLE=domoai` — скрипт напомнит после `stylize`.

## Файлы

| Путь | Назначение |
|------|------------|
| `tools/stern_comic_breakdowns.py` | Тексты разборов, подсказки по съёмке |
| `tools/stern_comic_video_pipeline.py` | init-matrix, stylize, list |
| `data/stern_comic_video_matrix.json` | Очередь публикации |
| `stern_comic_video.py` | Слот для scheduler |
| `media/stern/comic_raw/` | Исходники с телефона |
| `media/stern/comic_clips/` | Готовые mp4 для TG |

## Съёмка

См. поле `filming` в `tools/stern_comic_breakdowns.py` для каждого упражнения.  
Гиря 16 или 24 кг, фон — стена/кабинет, боковой ракурс для hinge/swing.
