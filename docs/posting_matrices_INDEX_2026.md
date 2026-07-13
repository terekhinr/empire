# Empire · индекс матриц постинга 2026

**Дата сборки:** 2026-07-13  
**Метод:** инвентарь литературы VPS + аудит каналов + OpenRouter (`deepseek/deepseek-chat`) + ручная сверка с `content_config.json`

---

## Матрицы по каналам

| Канал | Документ | Слотов/день | Режим | Ключевой JSON |
|-------|----------|-------------|-------|---------------|
| **Gdepar** | [`gdepar_posting_matrix_BOOKS_2026.md`](gdepar_posting_matrix_BOOKS_2026.md) | 3 | curated + книги | `gdepar_classic_banya.json` (160), `gdepar_book_excerpts.json` (**27**), `gdepar_duo_curated.json` (139) |
| | [`gdepar_posting_matrix_2026.md`](gdepar_posting_matrix_2026.md) | — | 14 треков для duo | `gdepar_angle_families.json` |
| **Stern** | [`stern_posting_matrix_2026.md`](stern_posting_matrix_2026.md) | 4 | curated + рубрики + видео | `stern_rubrics.json`, `stern_curated.json`, `stern_technique_matrix_161_200.json` |
| **Garden** | [`garden_posting_matrix_CURATED_2026.md`](garden_posting_matrix_CURATED_2026.md) | **1/нед** (заморозка) | только луна | `garden_kizima_calendar.json` (381) |
| **Lenin** | [`lenin_posting_matrix_2026.md`](lenin_posting_matrix_2026.md) | 3 | curated + ПСС | `lenin_rubrics.json` (91), `lenin_bedtime_stories.json` (245) |
| **Pension** | [`pension_posting_matrix_2026.md`](pension_posting_matrix_2026.md) | ручной | прогрев книги | `book_complete (1).md`, Crimson RAG |

---

## Сводная таблица решений

| Канал | Вердикт | Частота целевая | LLM |
|-------|---------|-----------------|-----|
| Gdepar | Реанимировать | 3–7/нед | **Выкл** |
| Stern | Сократить + углубить | 4/день curated | **Выкл** в 09:30–19:00 |
| Garden | Заморозка | 1/нед | **Выкл** |
| Lenin | Оптимизировать | 3/день | Только approve; календарь prebuilt |
| Pension | Ручной warmup | 0.5/нед → launch | **Выкл** |

---

## Литература VPS (кратко)

| Канал | Файлов | RAG chunks | Главная книга в матрице |
|-------|--------|------------|-------------------------|
| Gdepar | 28 | 4 550 | Хошев, Галицкий, Богданов |
| Stern | 25 | 5 419 | Поляков/Воропаев 1988, Цацулин, McGill |
| Garden | 19 | 5 793 | Кизима (+ Курдюмов curated) |
| Lenin | 58 | 14 647 | ПСС 45 т. |
| Pension | 27 | 6 428 | book_complete + Crimson |

---

## Сгенерированные артефакты (сессия)

| Файл | Описание |
|------|----------|
| `data/gdepar_book_excerpts.json` | 3 → **27** excerpt (авто из OCR) |
| `data/stern_rubrics_draft_polyakov_2026.json` | 6 черновиков «История гирь» — **проверить по книге** |
| `docs/audit/literature_revival_audit_JUL2026.md` | Аудит реанимации |
| `scripts/build_posting_matrices_openrouter.py` | Повторная генерация черновиков |

---

## Приоритет внедрения (2 недели)

1. **Gdepar:** дописать `note:` в 27 excerpt · OCR Богданов/Неумывакин  
2. **Stern:** merge `stern_rubrics_draft_polyakov_2026.json` после проверки  
3. **Garden:** создать `garden_curated.json` (12 постов) или оставить режим A  
4. **Lenin:** +5 `lenin_pss_topics` · отключить llm_free  
5. **Pension:** 4 ручных поста прогрева по матрице  

---

## Команды

```bash
# Матрицы через OpenRouter (черновики)
./venv/bin/python scripts/build_posting_matrices_openrouter.py

# Excerpt Gdepar
./venv/bin/python tools/build_gdepar_book_excerpts.py --auto "data/gdepar/*.rag.txt" --merge --limit 10

# Тесты
./venv/bin/pytest tests/test_gdepar_content.py tests/test_stern_rubrics.py tests/test_lenin_calendar_post.py -q
```

**OpenRouter:** Claude/Gemini — 403 на аккаунте; рабочая модель — `deepseek/deepseek-chat`.  
**Fal:** промпты в матрицах §6 каждого канала; генерация — по запросу редактора.
