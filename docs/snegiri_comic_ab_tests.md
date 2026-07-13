# A/B тесты мультиков · протокол

**Статус:** готово к запуску · **генерация каталога заблокирована** до победителей A/B  
**Канон:** `snegiri_kb/comic_briefs_data.json` · **промпты:** `scripts/render_comic_prompt.py`

---

## 0. Рабочие defaults (до A/B)

| Параметр | Default | Меняется если A/B скажет иначе |
|----------|---------|--------------------------------|
| Локация (все треки) | **`industrial_gym`** | vs `home_room` в A/B §1 |
| S-трек (пилот) | `home_room` + коврик | только контроль в A/B |
| K-трек (пилот) | `industrial_gym` | см. strategy_v2 |
| Рабочая рука | **правая** (одноручные) | нет |
| F от M | **обязательно** с референсом M | метод B vs C ниже |
| Farmer S7 base | **1×16 кг**, правая рука | эталон стартового курса |
| Farmer S7 advanced | **2×16 кг** | отдельный эталон `farmer_walk_2kb_*`, tier advanced |
| Язык подписей | `labels_ru` из brief | нет |
| Текущие 50 лент | все `needs_regen` | — |

---

## 1. A/B · Локация (4 изображения)

**Цель:** `industrial_gym` (профи, как YouTube) vs `home_room` (дом, коврик) — без штанги в кадре.  
**Канон v2:** [`snegiri_comic_strategy_v2.md`](snegiri_comic_strategy_v2.md) §3.

**Только M.** Два пилота (не три):

| # | slug | track | Зачем |
|---|------|-------|-------|
| 1 | `curl_up` | S | McGill, коврик, без гири |
| 2 | `swing` | K | флагман, гиря, side |

Для каждого slug — **2 варианта**:

```bash
# Вариант A — industrial gym (default в brief)
python3 scripts/render_comic_prompt.py --slug swing --performer m
python3 scripts/render_comic_prompt.py --slug curl_up --performer m

# Вариант B — дом / комната + коврик
python3 scripts/render_comic_prompt.py --slug swing --performer m --ab-location home_room
python3 scripts/render_comic_prompt.py --slug curl_up --performer m --ab-location home_room
```

**Имена файлов пилота (не в прод):**  
`assets/comics/_ab/swing_m_industrial.webp`, `swing_m_room.webp`, …

### Критерии (балл 1–5, заполняет человек)

| Критерий | A гараж | B комната |
|----------|---------|-----------|
| «Это дом, не зал» | | |
| Нет запрещённого реквизита | | |
| Читаемость на 360px | | |
| Совпадение с брендом (hero-poster) | | |
| Подходит под CV-ракурс | | |

**Решение:**
- S-трек → победитель для `home_room` vs унификация
- K-трек → победитель для `home_garage` vs унификация
- Зафиксировать в `comic_briefs_data.json` → `_meta.ab_winners.location`

---

## 2. A/B · Оборудование (гири) — base vs advanced

**Цель:** визуально отделить стартовый курс (1 гиря) от продвинутого (2 гири); прогнать **и в Gemini, и в Cursor**.

**Пилот:** `farmer_walk` · только M · после выбора локации из §1.

| Вариант | Команда | Файл пилота |
|---------|---------|-------------|
| **base** 1 гиря | `--tier base` | `farmer_walk_m_ab_base.webp` |
| **advanced** 2 гири | `--tier advanced` | `farmer_walk_2kb_m_ab_adv.webp` |

```bash
python3 scripts/render_comic_prompt.py --slug farmer_walk --performer m --tier base
python3 scripts/render_comic_prompt.py --slug farmer_walk --performer m --tier advanced
```

**Сравнить также** `suitcase_carry` (base, 1 гиря) — не путается ли с farmer base:

```bash
python3 scripts/render_comic_prompt.py --slug suitcase_carry --performer m --tier base
```

### Критерии

| Критерий | farmer 1 гиря | farmer 2 гири | suitcase 1 гиря |
|----------|---------------|---------------|-----------------|
| Читается «одна гиря дома» | | | |
| Отличимо от suitcase | | | |
| Классический farmer с двумя | n/a | | |
| Нет лишней гири на кадре | | | |
| Gemini vs Cursor одинаковый brief | | | |

**Решение:**
- Стартовый курс → всегда `tier: base`, одна 16 кг.
- `farmer_walk_2kb_*` — в UI только после разблокировки advanced (продуктово позже).
- Зафиксировать в `_meta.ab_winners.equipment_tier`.

---

## 3. A/B · M → F (4 ленты)

**Цель:** женщина не «разъезжается» относительно мужчины.

**Пилот:** `clean` (5 панелей, одноручная, сложная хореография).

### Шаг 1 — эталон M

```bash
python3 scripts/render_comic_prompt.py --slug clean --performer m > /tmp/clean_m_prompt.txt
```

Gemini/Cursor → QA по чеклисту → `clean_m_ab.webp`

### Шаг 2 — два метода F

| Метод | Как | Файл |
|-------|-----|------|
| **B** лента | `render_comic_prompt.py --slug clean --performer f` + attach `clean_m_ab` | `clean_f_strip_B.webp` |
| **C** кадры | 5 отдельных 4:3 кадров по панелям M, склейка `slice` или ручная | `clean_f_strip_C.webp` |

Промпт F (метод B) уже включает блок REFERENCE в `render_comic_prompt.py`.

### Критерии

| Критерий | B лента | C кадры |
|----------|---------|---------|
| Те же 5 фаз что M | | |
| Та же правая рука | | |
| Одна гиря 16 кг | | |
| Нет EN подписей | | |
| Визуальная связность панелей | | |
| Трудозатраты (1–5, 5=дорого) | | |

**Победитель** → `_meta.ab_winners.performer_pipeline` = `strip_from_m` | `panel_by_panel`

---

## 4. Чеклист QA (каждая лента)

```
[ ] Локация = winner A/B
[ ] FORBIDDEN: нет штанги/стоек/блинов/зала
[ ] tier = base → ровно 1 гиря (или 0 для S без гири)
[ ] tier = advanced → по brief advanced_variant
[ ] working_side = right (если задано)
[ ] Все labels_ru на кадре, кириллица
[ ] panels = N, порядок = panel_script
[ ] ERROR: одна #FF3300 линия
[ ] F: хореография = M
```

Провал → `status: needs_regen`, `qa_notes: "..."`

---

## 5. Порядок работ после A/B

1. Обновить `_meta.ab_winners` в briefs.
2. `python3 scripts/build_comic_briefs.py` (если меняли defaults).
3. `./scripts/sync_snegiri_comic_briefs.sh`
4. Волна 1 MVP: S1–S3, K1–K3, K6 (по brief, M→QA→F).
5. Волна 2: остальной каталог.
6. `slice_comic_strip.py` + sync phases только для `status: ok`.

---

## 6. Команды быстрого старта

```bash
# Собрать briefs
python3 scripts/build_comic_briefs.py
./scripts/sync_snegiri_comic_briefs.sh

# Мастер-промпт Gemini (первое сообщение сессии)
python3 scripts/render_comic_prompt.py --master

# Промпт одного упражнения
python3 scripts/render_comic_prompt.py --slug halo --performer m

# JSON для Cursor GenerateImage
python3 scripts/render_comic_prompt.py --slug farmer_walk --performer m --tier advanced
```

---

## 7. Журнал A/B (заполнять вручную)

| Дата | Тест | Победитель | Кто решил | Комментарий |
|------|------|------------|-----------|-------------|
| | location S | | | |
| | location K | | | |
| | equipment farmer 1 vs 2 | | | |
| | farmer vs suitcase (1 гиря) | | | |
| | M→F pipeline | | | |

*Пока таблица пуста — массовая генерация не начинается.*
