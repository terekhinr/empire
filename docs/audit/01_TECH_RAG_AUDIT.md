# Технический аудит RAG и автопостинга

**Роль:** Senior AI Engineer / Tech Lead. **Источник:** код `main.py`, `*_content.py`, `tools/build_rag.py`, `content_config.json`, `evaluate_rag.py`, `test_quality.py`.

---

## Ожидание / Реальность

| Область | Ожидание | Реальность (код) |
|---------|----------|------------------|
| RAG как ядро | Каждый пост = retrieval → grounded generation | **Гибрид:** ~45% слотов без LLM (curated, prebuilt, raw_news) |
| Retrieval | Точный семантический поиск | FAISS `similarity_search(k=5–10)`, MiniLM, **без rerank/MMR** |
| Объём | Качество | **~119 постов/нед** (17/день) — перепроизводство |
| Монетизация | Встроена | **Нет** P&L-метрик в `analytics.db` (мало `views_24h`) |
| Gdepar | Продукт | **Production** (`gdepar_app.py`, 89+ тестов) |
| Автопост 4 TG | Бизнес | **Не окупился** — дистрибуция = только публикация в канал |

---

## Узкие горлышки (по убыванию вреда)

1. **Нет дистрибуции** — контент в пустоту (ВК/Дзен не подключены массово).
2. **LLM-слоты commodity** — Garden/Stern generic советы; слабая реакция ЦА на тестах.
3. **RAG без rerank** — нерелевантные чанки → «ИИ-вода».
4. **God-file `main.py`** — сложно менять промпты без регрессий.
5. **119 постов/нед** — OPEX OpenRouter без ROI.

---

## Что оставить в коде

| Модуль | Вердикт |
|--------|---------|
| `gdepar_app.py`, парсеры OSM/Yandex | **Доить** |
| Curated: `classic_banya`, lenin PSS/book, `raw_news` Pension | **Оставить** |
| RAG Lenin/Gdepar книги | **Оставить** (уникальная база) |
| LLM Garden/Stern 28+20 слотов/нед | **Резать до 7–10** |
| Spy/нейро на Сад/Ленин | **Выключить** |

---

## Три изменения P0 (из аудита)

1. **Срез частоты** `content_config.json`: Stern/Garden до 7–10/нед; CTA на флагманы.
2. **`evaluate_rag.py`** в CI раз в неделю — faithfulness < 3 → не публиковать LLM-слот.
3. **Метрика:** лиды gdepar + продажи книги + нативки — не «посты вышли».

---

## LLM-as-Judge (факт из прогона)

Скрипт `evaluate_rag.py`: faithfulness/relevance/density 1–5. При 403 OpenRouter — fallback DeepSeek.  
`test_quality.py`: side-by-side RAG context vs post — видна «ИИ-шность» на Stern/Garden слотах.

---

*См. также: `02_ROI_MEDIA_AUDIT.md`, `04_STRATEGY.md`.*
