# Картинки для автопоста (без генерации на лету)

Цель: один раз напечатать картинки → прописать `image_file` в JSON → scheduler не вызывает Flux/Gemini при публикации.

**Провайдеры по каналу** (`data/curated_image_styles.json` → `image_provider`):
- **Gdepar (дуэт)** → **Gemini** (Nano Banana) — веники и банные сцены; Flux их не рисует
- **Stern** → **Fal Flux/dev** — офис/гиря lifestyle

```bash
# auto = по каналу (рекомендуется)
./venv/bin/python tools/generate_curated_images_nanobanana.py --channel gdepar   # gemini
./venv/bin/python tools/generate_curated_images_nanobanana.py --channel stern    # fal
```

Промпты веников Gdepar: канон из `gdepar_content.py` (`GDEPAR_VENIK_*_GEMINI_PROMPT`), не generic scene из манифеста.

## Сколько картинок

| Gdepar / канал | Слот | Картинки | Печатать? |
|----------------|------|----------|-----------|
| **Дуэт** (practice/evening/banya_week) | 11:00, 21:00 | ~139 `GDP-*` | **Да** — Nano Banana |
| **Классическая баня** | **15:00** | **160** портретов авторов | **Нет** — уже в `media/gdepar/classic/` |
| **Stern 19:00** | 19:00 | 15 базовых `STR-EV-*` | Да |
| **Stern 09:30** | 09:30 | ~68 постов | Да |

Классика: `data/gdepar_classic_banya.json` + `scripts/prefetch_gdepar_classic_images.py`.  
Портреты с Wikipedia/Commons, Flux/Nano Banana **не вызываются** (`is_curated_prebuilt` в scheduler).

Итого **Nano Banana**: ~222 (duo + stern). Классика в манифесте помечена `skip_nanobanana: true`.

Стили каналов: `data/curated_image_styles.json` (можно править `style_suffix` / `negative`).

---

## Пайплайн A — API (VPS, если есть quota)

```bash
cd /root/projects/empire

# 1. Манифест + paste-файлы (на случай ручного режима)
./venv/bin/python tools/build_nanobanana_image_manifest.py

# 2. Генерация (FAL_KEY + GEMINI_API_KEY в .env / empire.env)
./venv/bin/python tools/generate_curated_images_nanobanana.py --channel stern    # fal
./venv/bin/python tools/generate_curated_images_nanobanana.py --channel gdepar   # gemini
# Перегенерить одну (gdepar, веник):
./venv/bin/python tools/generate_curated_images_nanobanana.py --only GDP-PR-001 --provider gemini --force

# 3. Прописать image_file в JSON
./venv/bin/python tools/apply_curated_images.py
```

Переменные: `CURATED_IMAGE_GEMINI_MODEL`, `CURATED_IMAGE_GEMINI_SIZE` (как у веников).

---

## Пайплайн B — ручной Gemini UI

1. Новый чат → вставить `gemini_PASTE_MSG1_BOOT_NANOBANANA.txt`
2. По очереди батчи из `docs/content_factory/gemini_export/image_batch_requests/`:
   - `gdepar_images_part01.txt` …
   - `stern_images_part01.txt` …
3. Скачанные JPG положить в `media/_nanobanana_drop/` **с именами из `filename:`**
4. Импорт:

```bash
./venv/bin/python tools/import_nanobanana_drop_folder.py
```

---

## После привязки

- **Gdepar:** `gdepar_duo_curated.build_duo_curated_slot` уже отдаёт `prebuilt_img`
- **Stern:** `stern_curated.build_stern_curated_slot` теперь тоже (если `image_file` есть)
- Scheduler: `is_curated_prebuilt` → **без** `generate_image` на лету

Проверка одного поста:

```bash
./venv/bin/python -c "
import asyncio, stern_curated as s
print(asyncio.run(s.build_stern_curated_slot(slot='1900')))
"
```

---

## Хэштеги

Картинки не влияют на хэштеги. Третий тег — из рубрики `topic_raw` (`[Психология]` → `#психология`). Таблица в `tools/curated_image_lib.py` → `RUBRIC_HASHTAG`.

---

## Фаза 2 (позже)

В `curated_image_styles.json` заготовлены `garden`, `lenin`, `pension` (`_phase: 2`). Расширить `build_nanobanana_image_manifest.py` когда контент будет готов.

---

## Файлы

| Файл | Назначение |
|------|------------|
| `data/curated_image_styles.json` | стиль по каналу |
| `data/curated_topic_images_manifest.json` | все задачи |
| `tools/build_nanobanana_image_manifest.py` | сборка манифеста |
| `tools/generate_curated_images_nanobanana.py` | API batch |
| `tools/import_nanobanana_drop_folder.py` | импорт из UI |
| `tools/apply_curated_images.py` | → JSON |
