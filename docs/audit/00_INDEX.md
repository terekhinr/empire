# Empire · Пакет аудита и пайплайна 2026

**Назначение:** проверка финмодели в другом ИИ, годовой пайплайн, трекинг в planning PWA.  
**Обновлено:** 2026-07-15 (STATUS_SLICE — актуальный срез)

---

## Актуальный срез (июль 2026)

| Файл | Содержание |
|------|------------|
| **`2026-07-15_STATUS_SLICE.md`** | **Главный документ:** инфра, постинг, финансы, спринт 4 нед |
| `2026-07-15_FULL_INFRA_AUDIT.md` | Детальный аудит VPS + приоритеты P0/P1/P2 |
| `GEMINI_AUDIT_PROMPTS.md` | Промпты для повторного аудита в Gemini |
| `exports/` | Копии для Я.Диска и IDE |

---

## Состав пакета (исторический)

| # | Файл | Содержание |
|---|------|------------|
| 00 | `00_INDEX.md` | Этот файл — навигация |
| 01 | `01_TECH_RAG_AUDIT.md` | RAG, автопост, промпты, узкие места кода |
| 02 | `02_ROI_MEDIA_AUDIT.md` | Media Buyer: ROI четырёх TG, что доить/резать |
| 03 | `03_DIAGNOSTIC.md` | Ответы заказчика, пивот, ошибка «сначала аудитория» |
| 04 | `04_STRATEGY.md` | Два флагмана, спутники, решения июнь 2026 |
| 05 | `05_FINANCIAL_MODEL.md` | **Цифры с источниками** (книга, нативка, Где Пар, расходы) |
| 06 | `06_GDEPAR_MARKET.md` | Рынок бань, кейсы CPL, unit-экономика |
| 07 | `07_PIPELINE_BLOCKS.md` | Блоки и зависимости (для канваса) |
| 08 | `08_PIPELINE_YEAR.md` | Помесячный план июнь 2026 — май 2027 |
| 09 | `09_PROGRESS_TRACKER.md` | Чеклист с весами % → planning PWA |
| 10 | `10_REVISION_GEMINI.md` | Правка пайплайна (спринты, CPA-first) |
| 11 | `11_GEMINI_R2.md` | Раунд 2: CPL, churn, депозиты |
| 12 | `12_GEMINI_R3.md` | Bridge, комплаенс, триал |
| 13 | `13_GEMINI_R4.md` | Трафик Q3, 90 сек, НПД, tier триала |
| 14 | `14_GEMINI_R5.md` | Посевы→email, billsec, YT в августе |

**Воронка августа:** `docs/pension_august_funnel_2026.md`  
**Playbook (полный гайд):** `docs/EMPIRE_PIPELINE_PLAYBOOK_RU.md`

**Операционка:** `docs/empire_legal_structure.md` · `docs/gdepar_cpa_deposit.md` · `docs/gdepar_voice_bot.md` · `scripts/empire_finance_simulator.py`

---

## Как использовать

### Другой ИИ (финмодель)

1. Загрузить **`05_FINANCIAL_MODEL.md`** + **`08_PIPELINE_YEAR.md`** + **`11_GEMINI_R2.md`**.  
2. Прогнать: `./venv/bin/python scripts/empire_finance_simulator.py --cpl 400` и `--cpl 900`.  
   Голос (опц.): `--voice-from 8 --voice-call-uplift 0.05` — см. `docs/gdepar_voice_bot.md`.

### Obsidian Canvas

- Файл: `data/obsidian_vault/Empire/_canvas/empire-pipeline-2026.canvas`  
- Открыть в Obsidian → режим Canvas.  
- Узлы ссылаются на заметки в `Empire/_canon/` (после `sync_empire_obsidian.py --docs`).

### Planning PWA (аналог TickTick)

```bash
./venv/bin/python scripts/seed_empire_pipeline_2026.py
./venv/bin/python scripts/seed_empire_pipeline_2026.py --force   # пересоздать чеклисты
```

**Создаёт в planning.db:**

| Тип | Что |
|-----|-----|
| **Цель** | Empire · 100k ₽/мес к ноябрю 27 |
| **8 проектов** | Bridge, Пенсия (книга/медиа), Где Пар (данные/монетизация), Инфра, Спутники, Тех |
| **Итоговый чеклист** | `empire-pipeline-2026` — веса % из `09_PROGRESS_TRACKER.md` |
| **4 фазы** | `empire-pipeline-phase-0…3` — помесячный план из `08_PIPELINE_YEAR.md` |
| **7 блоков** | `empire-block-0,a…f` — по блокам трекера |
| **2 аудита** | `empire-audit-tech-p0`, `empire-audit-media-roi` |
| **14 вех** | Задачи с датами (launch 15 сен, bridge, CPL 15.11, 100k ноя 27…) |

Прогресс % итогового чеклиста = доля выполненных пунктов × вес.

---

## Финансовая цель (рев. Gemini)

| Веха | Цель |
|------|------|
| **Сентябрь 2026** | Launch + **bridge 35k** |
| **01.10.2026** | ИП супруги для gdepar |
| **Май 2027** | **50–70k ₽/мес** суммарно |
| **Ноябрь 2027 (стретч)** | **100 000 ₽/мес** |
| Год 1 net (июн 26 – май 27) | **120–180k ₽** |

Цены (299₽ книга, 8k нативка) — без изменений. Сдвинуты **воронка и сроки**.

---

## Быстрые ссылки на кейсы

| Кейс | Цифра |
|------|-------|
| Бабайкин, книга (самиздат) | **299 ₽** [Литрес](https://www.litres.ru/book/babaykin/na-pensiu-v-35-let-55699732/) |
| Бабайкин, книга (Эксмо 2025) | **769 ₽** |
| Баня СПб, Директ | **105 лидов × 1 195 ₽** [Rating Runeta](https://ratingruneta.ru/cases/case-13601/) |
| Нативка YT 5k subs | **3 000–15 000 ₽** (nano/micro, vc.ru/elama 2026) |
| Ridero: авторы без дохода | **65–68%** [РБК 2023](https://www.rbc.ru/technology_and_media/20/04/2023/643fe6199a7947390c03362b) |
