# Снегири · расписание постов (июль 2026)

**Режим:** 2–3 дня ручная публикация → `auto_publish.json` `enabled=true` для Stern.

## Недельная сетка (~8 постов)

| День | Время | Тип | Содержание |
|------|-------|-----|------------|
| **Пн** | 15:00 | `stern_lfk` | ЛФК-видео + разбор (пилот 3 шт.) |
| **Пн** | 19:00 | `stern_curated` | Голос Штерна + `media/stern/topics/*.jpg` |
| **Вт** | 09:30 | `stern_curated` | Утро / рутина |
| **Вт** | 10:00 | `stern_gallery` | Железная галерея (био атлетов) |
| **Ср** | 19:00 | `stern_curated` | Офис / быт |
| **Чт** | 09:30 | `stern_curated` | Утро |
| **Чт** | 10:00 | `stern_gallery` | Железная галерея |
| **Пт** | 19:00 | `stern_curated` | Вечер |
| **Сб** | 15:00 | `stern_technique` | Разбор техники гирь (YouTube) |
| **Сб** | 19:00 | `stern_curated` | Вечер |
| **Вс** | 09:30 | `stern_curated` | Утро |

**Видео:** 1 ЛФК + 1 техника гирь в неделю.  
**Галерея:** 2×/нед. **Curated:** 5×/нед — основной голос канала.

## Пайплайны

```bash
# ЛФК пилот (3 упражнения)
./venv/bin/python tools/stern_lfk_pipeline.py

# Фото галереи (Commons)
./venv/bin/python scripts/prefetch_stern_legacy_images.py

# Техника гирь (уже 40 клипов)
ls media/stern/technique_clips/*_sub.mp4 | wc -l
```

## Включить автопост (после ручной проверки)

В `data/auto_publish.json`:

1. `"enabled": true`
2. `"personas": { "stern": { "enabled": true, ... } }`
3. Рубрики: `stern_matrix_curated`, `stern_gallery`, `stern_technique_video`, `stern_lfk_video` → `"enabled": true`

Перезапуск: `systemctl restart empire_main` (или как у вас на VPS).

## Запасы

| Пул | Остаток |
|-----|---------|
| `stern_curated.json` | 167 постов, картинки `STR-RT-*.jpg` (151/167 на диске) |
| `stern_athletic_legacy` | ~147 ready не показаны |
| `stern_technique_matrix` | 34 клипа после 6 опубликованных |
| `stern_lfk_matrix` | 3 пилотных |

## Рубрики в паузе

- `russian_strongmen` (4 шт.) — контент вошёл в галерею
- `stern_comic_video` — своя съёмка, когда спина позволит
- LLM-слоты — отключены
