# Lenin TG · матрица постинга 2026

**Статус:** 3 поста/день · `auto_publish.json` → `lenin.enabled: false` (approve в боте)  
**Литература VPS:** ПСС 45 томов + Leniniana · 14 647 RAG chunks  
**Curated:** rubrics 91 · bedtime 245 · PSS topics 11

См. [`lenin_channel_editorial.md`](lenin_channel_editorial.md).

---

## 1. Ритм (3 поста / день, МСК)

| Слот | Роль | Тип в коде | Источник | LLM |
|------|------|------------|----------|-----|
| **08:30** | «В этот день…» | `lenin_calendar` | `data/lenin/revolutionary_calendar.txt` + шаблон | **Нет** (prebuilt) |
| **12:00** | Рубрика | `lenin_rubric` | `data/lenin_rubrics.json` | **Нет** |
| **19:00** | Вечер | `lenin_pss` · `lenin_book` · `marxism` · `channel_support` | ПСС RAG · bedtime JSON | PSS: RAG без LLM где возможно |

---

## 2. Матрица по дням недели

| День | 08:30 | 12:00 рубрика | 19:00 |
|------|-------|---------------|-------|
| **Пн** | Календарь | `lenin_rubric` (ротация lit/art/bio/cinema) | **ПСС** `lenin_pss` |
| **Вт** | Календарь | `lenin_rubric` | **Книга** `lenin_book` (bedtime / Leniniana) |
| **Ср** | Календарь | `lenin_rubric` | **ПСС** |
| **Чт** | Календарь | `lenin_rubric` | **Марксизм** (1×/нед, угол из config) |
| **Пт** | Календарь | `lenin_rubric` | **Книга** |
| **Сб** | Календарь | `lenin_rubric` | **ПСС** |
| **Вс** | Календарь | `lenin_rubric` | **Поддержка канала** `channel_support` |

---

## 3. Рубрики 12:00 (`lenin_rubrics.json`)

| Rubric key | Записей | Содержание | Ротация |
|------------|---------|------------|---------|
| `literature` | 11 | Стихи, проза о Ленине | `lenin_rubrics_used.json` |
| `art` | 4 | Плакаты, живопись | |
| `biography` | 71 | Факты, даты (вкл. Danilkin) | основной пул |
| `cinema` | 5 | Кадры, фильмы | |

**Формат поста:** `quote` в blockquote · `source` — «Источник: …» · `image_file` Commons · `note` только в JSON для редактора.

---

## 4. ПСС 19:00 — темы (`lenin_pss_topics.json`)

| topic id | Угол |
|----------|------|
| `pss_imperialism_trade` | Империализм, торговля |
| `pss_trade_unions` | Профсоюзы |
| `pss_peasant_land` | Крестьянин, земля |
| `pss_state_apparatus` | Аппарат |
| `pss_education` | Образование |
| `pss_cooperatives` | Кооперация |
| `pss_youth` | Молодёжь |
| `pss_international` | Интернационал |
| `pss_electricity` | Электрификация |
| `pss_army_supply` | Армия, снабжение |
| `pss_labor_productivity` | Производительность труда |

**Добавить из неиспользованных томов:** Т.32 (профсоюзы и массы), Т.33 (кооперативный план), Т.35 (цензура, парижская корреспонденция).

**Стоп-фразы в коде:** «Сим победиши», «актуально сегодня», «парадокс?» — не допускать.

---

## 5. Книги VPS → слоты

| Источник | Слот | JSON / путь |
|----------|------|-------------|
| ПСС т. 1–45 | 19:00 PSS | `vector_db/lenin` + topics |
| Данилкин «Пантократор» | 12:00 bio | `lenin_rubrics` danilkin_* |
| Leniniana PDF | 19:00 book | `lenin_bedtime_stories.json` (245) |
| `revolutionary_calendar.txt` | 08:30 | prebuilt |
| Кононов, Замостьянов сказки | book | `kb_sources/lenin/books/` |

---

## 6. Визуал и Fal

| Слот | Commons | Fal prompt |
|------|---------|------------|
| 08:30 | Архивные даты, газеты | `1917 newspaper typography sepia minimal` |
| 12:00 | Портреты, плакаты CC | `Soviet constructivist poster style red black geometric no text` |
| 19:00 PSS | Скан страницы / портрет | `book page open Cyrillic historical document warm light` |

---

## 7. Ротация и анти-повторы

| Пул | Правило |
|-----|---------|
| Календарь | 1 дата = 1 пост, без LLM-воды |
| Rubrics | id не повторять до исчерпания |
| PSS | topic rotation + chunk из RAG |
| Bedtime | 245 stories, cooldown |
| **llm_free** | **отключить** (23 плохих поста в аудите) |

---

## 8. Чеклист редактора

- [ ] 08:30 начинается с «В этот день (по старому календарю …)»
- [ ] 12:00 — только JSON, длина quote адекватна
- [ ] 19:00 PSS — фрагмент реальный, источник том+страница
- [ ] Нет «актуально сегодня»
- [ ] Фото: лицензия Commons

---

## 9. Следующие шаги

```bash
./venv/bin/python tools/build_rag.py --persona lenin --force  # после новых PDF
./venv/bin/pytest tests/test_lenin_rubrics.py tests/test_lenin_calendar_post.py -q
```

+5 topics в `lenin_pss_topics.json` из Т.32–35.  
Опционально P2: аудио ПСС (TTS) — отдельный пайплайн.
