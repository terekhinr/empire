# Импорт постов из Gemini Share

**Твой чат:** https://share.gemini.google/hLl6LaMg9e0X

Сервер/VPS **не может** открыть share-ссылку (нужен вход в Google).  
Посты попадают в Empire только после **копирования ответов в файлы**.

## Быстрый способ (5 минут)

1. Открой share в браузере (где ты залогинен в Google).
2. Для **каждого ответа Gemini** с постами:
   - выдели **весь** markdown (от первого `---` / `id:` до блока `## CHECKLIST`);
   - вставь в новый файл:
     ```
     docs/content_factory/gemini_export/gemini-code-<любое-имя>.md
     ```
   - пример: `gemini-code-gdepar_02_partA.md`
3. На VPS или локально:
   ```bash
   cd /path/to/empire
   ./venv/bin/python tools/ingest_gemini_content_export.py
   ```
4. Проверь: `docs/content_factory/gemini_export/generated/GEMINI_OUTPUT_STATUS.md`

## Что должно быть в файле

- **Gdepar:** блоки с `id: duo_...`, `pool:`, `headline:`, тело Михалыч/Кириллыч
- **Stern:** `id: stern_...`, `slot:`, `topic_raw:`, тело с `🏛️`
- В конце: `POST_COUNT: 6` (или сколько в задании)
- **Без** «остальные посты в том же стиле» — только полный текст

## Куда попадает после ingest

| Канал | Файл Empire | Слоты автопоста |
|-------|-------------|-----------------|
| Gdepar `[Дуэт]` | `data/gdepar_duo_curated.json` | 11:00 / 21:00 |
| Stern 09:30 / 19:00 | `data/stern_curated.json` | 09:30 / 19:00 |

## Порядок батчей (если выгружаешь из того же чата)

1. `gdepar_02_partA` … `gdepar_12_partB` (см. `batch_requests/`)
2. `stern_08_partA` … `stern_13_partB`

## Если файл обрезан

В `GEMINI_OUTPUT_STATUS.md` попадёт в список TRUNCATED — перегенерируй этот подбатч в Gemini и сохрани заново.

## После импорта на VPS

```bash
sudo systemctl restart empire_main
```
