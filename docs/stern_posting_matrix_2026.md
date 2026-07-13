# Stern TG · матрица постинга 2026 (книги + curated)

**Статус:** `content_config.json` — **4 слота/день** (11:00 LLM убран из schedule)  
**Продукт:** воронка в [Снегири](https://snegirinegiri.ru)  
**Литература VPS:** 25 PDF, 5 419 chunks · рубрики 21 entry · athletic_legacy 301 · stern_curated 151

См. [`stern_kettlebell_history_sources.md`](stern_kettlebell_history_sources.md) · черновик из Полякова: `data/stern_rubrics_draft_polyakov_2026.json` (6 entries, **проверить по книге**).

---

## 1. Ритм (4 поста / день, МСК)

| Слот | Роль | Тип в коде | Источник | LLM |
|------|------|------------|----------|-----|
| **09:30** | Утро / рутина | `stern_curated` slot `0930` | `data/stern_curated.json` | **Нет** |
| **10:00** | Рубрика недели | `stern_rubric` | `data/stern_rubrics.json` | **Нет** |
| **15:00** | Техника | `stern_technique` (сб) · `weekly_test` (ср) | `stern_technique_matrix_161_200.json` | **Нет** |
| **19:00** | Вечер | `stern_curated` slot `1900` · `weekly_recap` (вс) | `stern_curated.json` | **Нет** |

---

## 2. Матрица по дням недели

| День | 09:30 | 10:00 рубрика | 15:00 | 19:00 |
|------|-------|---------------|-------|-------|
| **Пн** | curated 0930 | **kettlebell_history** | technique video | curated 1900 |
| **Вт** | curated 0930 | **athletic_legacy** (из JSON 301) | technique | curated 1900 |
| **Ср** | curated 0930 | **sports_med** | **weekly_test** | curated 1900 |
| **Чт** | curated 0930 | **equipment** | technique | curated 1900 |
| **Пт** | curated 0930 | **sports_med** (2-й за неделю) | technique | curated 1900 |
| **Сб** | curated 0930 | **kettlebell_fitness** | **stern_technique** видео | curated 1900 |
| **Вс** | curated 0930 | ротация rubric | technique | **weekly_recap** |

**Ротация 10:00** (`stern_content.RUBRIC_ROTATION`):  
`kettlebell_history` → `athletic_legacy` → `sports_med` → `equipment` → `sports_med` (по weekday % 5).

---

## 3. Книги VPS → рубрики

| Книга | Rubric / слот | Темы серии | Posts цель | Действие |
|-------|---------------|------------|------------|----------|
| Поляков/Воропаев «Гиревой спорт» 1988 | `kettlebell_history` | Комиссия СССР, нормативы 80-х, массовый спорт | +6 (черновик готов) | merge draft после проверки |
| Цацулин 2015 + From Russia with Tough Love | `kettlebell_fitness` | Методика, ошибки новичка | +8 | excerpt → JSON |
| McGill Back Mechanic / Ultimate Back | `sports_med` | Спина, схемы (**без ™ McGill**) | +6 | PDF-скрин + дисклеймер |
| Епифанов ЛФК 2006 | `sports_med` | Упражнения при боли | +5 | curated |
| «Приросший к стулу» | `stern_curated` 0930 | Офисная спина | +4 | цитата + 3 упражнения |
| Майерс «Анатомические поезда» | `equipment` / новая `fascia` | Гиря и фасции | +4 | схемы |
| Мохан биохимия | `sports_med` | Питание, восстановление | +3 | цифры из книги |
| Фицджеральд психология | `stern_curated` 1900 | Мотивация | +4 | без «кортизол»-спама |
| Ильин «Психология спорта» | 1900 curated | Срывы, цели | +3 | |
| Маматов 2021 | **не LLM** | 2 проверенные цитаты max | 2 | убрать из автогенерации |

**Новая рубрика (опционально):** `fascia_lines` в `stern_rubrics.json` — 1×/мес из Майерса.

---

## 4. Видео 15:00 (суббота)

- Очередь: `data/stern_technique_matrix_161_200.json` (40 клипов)
- Код: `stern_technique.py` · медиа: `media/stern/technique_clips/*_sub.mp4`
- Источники книг: Цацулин, McGill — для **субтитров**, не для LLM-текста поста

---

## 5. Визуал и Fal

| Рубрика | Commons | Fal prompt |
|---------|---------|------------|
| kettlebell_history | Торговые гири, архив | `Soviet cast iron kettlebell trade weight 19th century museum photo style` |
| sports_med | Анатомия, схема спины | `minimal anatomy diagram lower back muscles educational no text` |
| equipment | Гиря, коврик | `single kettlebell industrial gym concrete floor dramatic light` |
| technique video | кадр из клипа | не Fal |

**Хэштеги:** ≤3 релевантных; убрать спам 5+.

---

## 6. Ротация и анти-повторы

| Пул | Cooldown |
|-----|----------|
| `stern_rubrics_used.json` | без повтора id до исчерпания пула |
| `stern_curated` | slot 0930 / 1900 разные пулы |
| `athletic_legacy` | 301 entries, status `ready` |
| Маматов / «гиря не просто» | **запрещены** в новых постах |

---

## 7. Чеклист редактора

- [ ] 10:00 — тело ≥260 символов, `note` не пустой
- [ ] McGill — «методика канадского специалиста по спине», не trademark
- [ ] Медицина — «не замена врачу»
- [ ] Сб 15:00 — видео с субтитрами загружено
- [ ] Ссылка на snegirinegi.ru — 1×/нед нативно в curated

---

## 8. Следующие шаги

```bash
# Проверить черновик Полякова
cat data/stern_rubrics_draft_polyakov_2026.json

# После правки — merge в stern_rubrics.json entries kettlebell_history
./venv/bin/pytest tests/test_stern_rubrics.py -q

# Картинки рубрик
./venv/bin/python scripts/prefetch_stern_rubric_images.py
```

Отключить остатки LLM в `auto_publish.json` для stern (plan/test если ещё есть).
