# Сводка аудита Empire · для копирования

**Дата:** 2026-07-15 · **VPS:** moderate-amethys · **Доходы:** 0 ₽

---

## Почему зависало / не копировалось из `data/`

В `.cursorignore` был **весь каталог `data/`** (~4 ГБ PDF/MP3). Cursor не индексировал и **блокировал копирование** — это сделано специально для VPS 8 GB RAM.

**Исправлено:** игнорируются только тяжёлые подпапки (`data/stern/`, `data/audio/`…), а лёгкие JSON (`empire_weekly_kpi.json`, `empire_finance_ledger.json`) и `data/infra/` — **доступны в IDE**.

Копируемые копии всегда здесь: `docs/audit/exports/`

---

## Постинг за неделю (эффективность)

| Персона | Опубликовано | Skip | Success |
|---------|--------------|------|---------|
| garden | 21 | 1 | 95% |
| gdepar | 20 | 1 | 95% |
| stern | 19 | 2 | 90% |
| lenin | 12 | 7 | **63%** |
| **Итого** | **72** | **11** | **87%** |

**Проблема Lenin:** skip из-за короткого текста (`short:247<500` и т.д.) — нужны длиннее черновики в очереди.

**Оценка:** автопост приемлемый; без Metrika ROI постинга не измерить.

Автообновление: `empire-weekly-posting-metrics.timer` (вс 08:30 МСК) → `data/empire_weekly_kpi.json`

---

## ПО на VPS (кратко)

| Сервис | Статус |
|--------|--------|
| empire_main, empire_worker | ✅ |
| empire_gdepar, empire_webapp | ✅ |
| empire_dashboard, empire_sales | ✅ |
| nginx | ✅ |
| amnezia-awg2 (Docker) | ✅ |
| empire-db-1 (Postgres) | ⚠ проверить нужность |

Полный список: `docs/audit/exports/vps-software-inventory.txt`

---

## Проекты: что первым, что подождать

### P0 (2–4 недели)

1. **Yandex Metrika** — gdepar.ru + neverretire.ru (блокер всех KPI)
2. **Pension** — финал книги, yt-001, `/buy` pre-sale
3. **Lenin queue** — длиннее посты (убрать skip 63%)
4. **Gdepar** — через 2–4 нед решение по `GDEPAR_ASSISTANT_LLM_PCT`

### P1 (1–2 месяца)

- VK/Дзен адаптеры omni-publish
- Stern tripwire YooKassa (после 3 видео)
- Garden PDF + ВК

### P2 (по триггерам)

- PostgreSQL (SQLite > 1 GB)
- 2-й VPS для VPN
- Нейрокомментинг

---

## Финансы и unit economics

### Расходы сейчас (₽/мес)

| Статья | Сумма |
|--------|-------|
| VPS Austria 4/8/120 | 2 400 |
| Cursor | 1 500 |
| OpenRouter | 500–1 500 |
| Домены | ~300 |
| **Итого** | **~4 700–5 000** |

Факт в ledger: VPS 2 373 ₽ (2026-05-27).

### Доходы

**Сейчас: 0 ₽**

### Break-even (сколько продаж/мес покрыть VPS)

| Продукт | Цена | Нужно продаж/мес |
|---------|------|------------------|
| Stern tripwire | 390 ₽ | ~7 |
| Garden PDF | 290 ₽ | ~9 |
| Pension книга ~490 ₽ | 490 ₽ | ~5 |

### Прогноз (консервативный)

| Период | ₽ |
|--------|---|
| 2026 Q3 | 0 |
| 2026 Q4 | ~48 000 |
| 2027 H1 | ~300 000 |

**Правило:** расходы > 6 000 ₽/мес **2 месяца** без выручки → стоп реклама, ревизия LLM.

---

## Промпты Gemini

См. [`GEMINI_AUDIT_PROMPTS.md`](../GEMINI_AUDIT_PROMPTS.md) — 6 готовых блоков (инфра, проекты, финансы, постинг, роутер, re-audit).

---

## Команды

```bash
# Обновить KPI постинга вручную
./venv/bin/python scripts/empire_weekly_posting_metrics.py

# Скопировать всё в exports/
sudo bash scripts/export_audit_snapshots.sh

# Инвентаризация ПО
sudo bash scripts/vps_software_inventory.sh
```
