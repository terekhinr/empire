# Content Factory — Gemini (Gdepar + Stern)

## Архив для Gemini

```bash
./scripts/export_gemini_content_factory.sh
```

Результат: **`docs/content_factory/gemini_content_factory_bundle.tar.gz`** (~22 файла, 25 батчей).

Первое сообщение в Gemini: скопировать **`gemini_export/gemini_PASTE_FIRST.txt`**.

## Фазы

| Фаза | Промпт | Что получаем |
|------|--------|--------------|
| **0** | `gemini_PROMPT_PHASE0_REVIEW.txt` | Оценка матрицы и плана **до** генерации |
| **1** | `GENERATE_gdepar` / `GENERATE_stern` | Батчи по `BATCH_MANIFEST_sept2026.md` |
| **2** | `QUALITY_BATCH` + `QUALITY_REVIEW` | Приёмка, переписывание P0 |
| **3** | импорт на VPS | `parse_gdepar_duo_import.py` |

## Объём до 15.09.2026

| Канал | Постов |
|-------|--------|
| Gdepar duo | ~139 |
| Stern текст | ~149 |
| **Итого** | **~288** |

Уже есть 5 постов Gdepar — см. `EXISTING_gdepar_duo.json`.

## Решения (кратко)

- **Gdepar:** только ручной дуэт, без LLM в канал; без фейковых °C и %.
- **Stern:** ≤3 хэштега; сб видео чемпионов; своя гиря на паузе (Modic).

Старые файлы в `docs/content_factory/*.txt` — дубликаты; канон в `gemini_export/`.
