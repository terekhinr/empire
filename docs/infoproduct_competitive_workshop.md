# Воркшоп: инфопродукты Garden и Stern (конкуренты + «продавец–покупатель»)

Цель: понять, **не слабее ли наши** tripwire/курс, чем типичные конкуренты, и отшлифовать оффер до публикации оплаты.

## Наши продукты (MVP)

| Канал | Код | Цена | Файл ТЗ |
|-------|-----|------|---------|
| **Сад** | `garden_tripwire_checklist` | 290 ₽ | `docs/garden_infoproduct_tz.md` |
| **Сад** | `garden_guide_4weeks` | 1290 ₽ | `data/garden_deliverables/` |
| **Штерн** | `tripwire_office` | 390 ₽ | `data/stern_products.json` |
| **Штерн** | `course_iron_spine_21` | 4900 ₽ | `data/stern_products.json` |

Позиционирование сада: `docs/garden_positioning.md` (не энциклопедия, 1–2 действия + тест на грядке).

---

## Шаг 1 — конкуренты (ручной список + дополнение)

**Готовый прогон (май 2026):** [`docs/infoproduct_competitive_analysis_2026.md`](infoproduct_competitive_analysis_2026.md) + [`data/infoproduct_competitor_landscape.json`](../data/infoproduct_competitor_landscape.json).

Заполните `data/infoproduct_competitor_landscape.json` реальными ссылками (или обновляйте раз в квартал):

**Сад:** умный огород / натуральное земледеление / чек-листы PDF / мини-курсы в Telegram.  
**Штерн:** гиря + спина / офисный фитнес / «21 день» / McGill-лайт без копирования бренда.

Критерии сравнения (1–5):

1. Конкретика (можно сделать завтра на грядке / в зале)  
2. Объём «воды»  
3. Цена / воспринимаемая ценность  
4. Отстройка от «100 советов» / «стань героем»  
5. Доверие (автор, дисклеймеры, медицина)

---

## Шаг 2 — чат «продавец ↔ покупатель» (ИИ)

Скрипт симулирует **два прохода** без отдельного UI-чата:

```bash
cd /root/projects/empire
./venv/bin/python tools/infoproduct_workshop.py --persona garden --product garden_tripwire_checklist
./venv/bin/python tools/infoproduct_workshop.py --persona stern --product tripwire_office
```

Результат: `data/infoproduct_workshop_<persona>_<product>.md` — диалог + вывод «что усилить».

**Как организовать живой чат:** два окна Cursor / два агента с ролями:

- **Покупатель:** «дачник 45+, устал от воды, боится навоза и химии»  
- **Продавец:** только факты из `garden_products.json` + positioning, без выдуманных гарантий  

Правило: продавец отвечает коротко; если покупатель ловит воду — фиксируем правку в PDF.

---

## Шаг 3 — правки в продукт

| Сигнал из чата | Действие |
|----------------|----------|
| «Не понял, что получу» | Уточнить обложку и 3 буллета в `garden_promo_copy.json` / stern аналог |
| «Дорого за PDF» | Tripwire 290/390 — ок; усилить «что внутри за 60 сек теста» |
| «Похоже на всех» | Добавить полевой тест из positioning |
| «Нет доверия» | Дисклеймер + «или аналоги» для добавок (Штерн) |

---

## Шаг 4 — включение оплаты

Только после 2–3 успешных прогонов workshop и правок PDF:

- `payments_enabled: true` в `data/garden_products.json` / `stern_products.json`  
- YooKassa webhook (см. `docs/garden_infoproduct_tz.md`)

---

## Связь с контентом канала

- **Сад 20:00** — календарь Кизимы (`kizima_lunar`), не конкурирует с tripwire.  
- **Штерн** — рубрики 09:00 + RAG; tripwire «офис» — отдельная воронка в боте.
