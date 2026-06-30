# Статус выгрузки Gemini (авторазбор)

- Источники: `docs/audit/gemini_export, docs/content_factory/gemini_export`
- Файлов `gemini-code-*.md`: 55
- **Gdepar постов собрано:** 134
- **Stern постов собрано:** 151
- **Всего уникальных id:** 286
- **Записей в gdepar_duo_curated.json:** 139

## Обрезанные файлы (перегенерировать в Gemini)

- `gemini-code-1782576897800.md`
- `gemini-code-1782576901732.md`
- `gemini-code-1782576918029.md`
- `gemini-code-1782590635766.md`
- `gemini-code-1782590696261.md`
- `gemini-code-1782590737106.md`

## Дубликаты id (пропущены)

- `duo_silence_parka_04`
- `duo_review_hot_05`
- `duo_bannik_06`
- `stern_1900_burnout_01`
- `stern_1900_sleep_03`
- `stern_1900_sleep_03`
- `stern_1900_relapse_05`
- `duo_silence_parka_04`
- `duo_review_hot_05`
- `duo_bannik_06`
- `stern_1900_ev_001_b08`

## Чего не хватает до 15.09

| Канал | есть | цель | осталось |
|-------|------|------|----------|
| Gdepar duo | 134 | ~139 | 5 |
| Stern текст | 151 | ~149 | 0 |

## Следующие батчи (манифест)

- Gdepar: файлы с TRUNCATED / по 1 посту — полные батчи 02–12
- Stern 1900: добить `stern_08` … `stern_13` до 12 постов в батче
- Фаза 0 в выгрузке **не найдена** — опционально

## Импорт

- Gdepar: `data/gdepar_duo_curated.json` обновлён
- Stern: `docs/content_factory/gemini_export/generated/stern_all_ingested.md`
- Сырые файлы: `generated/raw/`

## Замечания редактора

- P0 (фейк-цифры, «слушай») в выгрузке **не найдены**.
- Stern `stern_0930_yoga_tgu_66` — get-up; проверить при Modic.
- Заголовок `Полки — не для слабаков` — заменить на нейтральный при approve.