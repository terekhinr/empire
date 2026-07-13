# Gdepar TG · матрица постинга 2026 (книги + curated)

**Статус:** актуально с `content_config.json` (июль 2026)  
**Режим:** без LLM в 11:00/21:00 — только `duo_curated`, `book_rubric`, `classic_banya`, `promo_map`  
**Литература VPS:** 28 файлов, 4 550 RAG-chunks · `data/gdepar_book_excerpts.json` — **27** excerpt (авто+ручные)

См. также: [`gdepar_posting_matrix_2026.md`](gdepar_posting_matrix_2026.md) (14 треков для будущих duo), [`gdepar_posting_matrix.md`](gdepar_posting_matrix.md) (анти-повторы).

---

## 1. Ритм (3 поста / день, МСК)

| Слот | Роль | Тип в коде | JSON / источник | LLM |
|------|------|------------|-----------------|-----|
| **11:00** | Практика / промо / книга | `promo_map` · `book_rubric` · `duo_curated` | `gdepar_promo_copy.json` · `gdepar_book_excerpts.json` · `gdepar_duo_curated.json` | **Нет** |
| **15:00** | Классика | `classic_banya` | `gdepar_classic_banya.json` (160) | **Нет** |
| **21:00** | Вечер / история | `duo_curated` · `book_rubric` | pools `evening` / `practice` · excerpts | **Нет** |

**Принцип:** утро — польза или карта; день — русская классика; вечер — диалог или фрагмент книги.

---

## 2. Матрица по дням недели (как в `content_config.json`)

| День | 11:00 | 15:00 | 21:00 |
|------|-------|-------|-------|
| **Пн** | `promo_map` — карта [gdepar.ru](https://gdepar.ru) | `classic_banya` | `duo_curated` pool **evening** |
| **Вт** | `book_rubric` **pechi_banya** (Хошев) | `classic_banya` | `duo_curated` evening |
| **Ср** | `duo_curated` pool **practice** | `classic_banya` | `duo_curated` evening |
| **Чт** | `duo_curated` practice | `classic_banya` | `book_rubric` **istoriya_bani** (Галицкий, Богданов) |
| **Пт** | `duo_curated` practice | `classic_banya` | `duo_curated` evening |
| **Сб** | `duo_curated` practice | `classic_banya` | `duo_curated` evening |
| **Вс** | `duo_curated` practice | `classic_banya` | `duo_curated` evening |

> **Пт 21:00** — кандидат на `book_rubric: zdorovje_par` (Пустовойтов, Неумывакин) после наполнения excerpt.

---

## 3. Книги VPS → рубрики → слоты

| Книга (VPS) | Rubric key | Серия постов | Слот | Excerpt сейчас | Цель |
|-------------|------------|--------------|------|----------------|------|
| Хошев «Дачные бани и печи» | `pechi_banya` | Печь, каменка, пар | Вт 11:00 | ~10 | 25 |
| Галицкий «Щедрый жар» | `istoriya_bani` | Этнография, веники | Чт 21:00 | ~10 | 20 |
| Богданов «Три века петербургской бани» | `istoriya_bani` | Петербург, сословия | Чт 21:00 | 0 → OCR | 12 |
| Пустовойтов «Баня лечит» | `zdorovje_par` | Веники, запаривание | Пт/Вс 21:00 | ~7 | 15 |
| Неумывакин «Мифы и реальность» | `zdorovje_par` | Разбор мифов + дисклеймер | 21:00 | 0 | 8 |
| Микулин «Активное долголетие» | `zdorovje_par` | Закаливание (осторожно) | 11:00 duo | 0 | 6 |
| Фальковский «Водоснабжение» | `istoriya_bani` | До водопровода | 21:00 | 0 | 5 |
| Воеводина «Магия мягкой бани» | `pechi_banya` | Мягкий пар | 11:00 book | 0 | 6 |
| Ушбаев «Целебные травы» | — (duo вечер) | Чай, травы | 21:00 duo | — | 8 duo |
| Иванченко «Тайны закала» | `zdorovje_par` | Закаливание | 21:00 | kb_sources | 5 |

**Файлы:** `data/gdepar_book_excerpts.json` · каталог `data/gdepar_books_catalog.json` · импорт `tools/build_gdepar_book_excerpts.py`

**Cooldown excerpt:** 45 дней на id (`gdepar_book_excerpts_used.json`).

---

## 4. Пулы duo_curated (139 записей)

| Pool | Когда | Содержание |
|------|-------|------------|
| `practice` | Ср–Вс 11:00 | Михалыч↔Кириллыч: печь, веник, ошибки (без «Кириллыч, слушай» в заходе) |
| `evening` | Пн–Сб 21:00 | Байки, чай, философия, мягкий юмор |

Ротация: `gdepar_duo_curated_used.json` · анти-клише: `gdepar_angle_families.json`

---

## 5. Классика 15:00 (160 записей)

- Авторы: Пушкин, Толстой, Достоевский, Чехов, Гоголь, Астафьев, Шолохов…
- Cooldown: **56 дней** на id
- Визуал: `media/gdepar/classic/` · Commons
- Obsidian-база: `data/obsidian_vault/Empire/gdepar/База постов — Русская баня…`

---

## 6. Визуал и Fal

| Тип | Источник | Fal prompt (шаблон) |
|-----|----------|---------------------|
| Промо карта | Скрин gdepar.ru | не генерировать AI-картинку |
| Классика | Commons / ретро | `Russian banya 19th century wood interior steam warm light illustration` |
| Книга | Обложка / схема из PDF | `technical diagram Russian bath stove cross-section no text vintage` |
| Duo | Свои фото веника/чая | `still life birch venik tea thermos Russian banya dressing room` |

**Приоритет:** свои фото → Commons → Fal (с пометкой «иллюстрация»).

---

## 7. Ротация и анти-повторы

| Слой | Механизм |
|------|----------|
| Классика | 160 id × 56 дней ≈ 23 недели без повтора |
| Book excerpt | 45 дней / id; 3 рубрики чередуются |
| Duo | Семейства G1–G14 в `gdepar_angle_families.json` |
| Промо | 3 варианта в `gdepar_promo_copy.json` |

---

## 8. Чеклист редактора

- [ ] Пн 11:00 — promo без AI-картинки, UTM `weekly_map`
- [ ] Book excerpt — `note:` от Михалыча (2–4 предложения), не пустой
- [ ] Медицина (Неумывакин, Пустовойтов) — «не медсовет»
- [ ] Нет «Кириллыч, слушай» в первой строке duo
- [ ] Картинка не «финская сауна» к тексту про русскую печь

---

## 9. Следующие шаги в репо

```bash
# Черновики из OCR (ручная правка note:)
./venv/bin/python tools/build_gdepar_book_excerpts.py --auto "data/gdepar/Богданов*.pdf" --rubric istoriya_bani --limit 10 --merge

# Проверка
./venv/bin/pytest tests/test_gdepar_content.py -q
```

Добавить в каталог: `bogdanov_spb_2000`, `neumyvakin_2010` → прогнать excerpt.
