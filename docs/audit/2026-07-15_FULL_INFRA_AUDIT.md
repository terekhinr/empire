# Полный аудит Empire · 2026-07-15

**VPS:** moderate-amethys · 193.233.232.48 · Tailscale `empire-vps-ts`  
**Дом:** Flint 2 + HA TOX1 · podkop / zapret / Amnezia / Transmission  
**Статус доходов:** 0 ₽ (pre-revenue)

---

## 1. ПО на VPS (инвентаризация)

| Слой | Компоненты | Статус |
|------|------------|--------|
| **Web** | nginx, certbot, gdepar :8001, neverretire :8000, sales :8002, hub Streamlit :8501 | ✅ prod |
| **Bots** | empire_main (scheduler+autopost), empire_worker, garden/stern/donate bots | ✅ |
| **Infra** | night-pipeline, daily-audit, diagnostics-watchdog, rclone→Я.Диск | ✅ |
| **VPN/дом** | bootstrap :8789, reverse SSH :6223, Amnezia Docker, HA bridge :8766 | ✅ |
| **DB** | empire.db (SQLite WAL), analytics/sales — каркас | 🔄 |
| **Docker** | amnezia-awg2 (если запущен), compose stepanich/postgres — проверить нужность | ⚠ |
| **Мониторинг NEW** | router-watchdog, morning-brief, weekly-posting-metrics | 🆕 deploy |

**Рекомендация:** `scripts/vps_software_inventory.sh` — еженедельно в audit.

---

## 2. Проекты и каналы

| Персона | TG | Сайт | Автопост | Монетизация | Готовность |
|---------|-----|------|----------|-------------|------------|
| **Pension** | ✅ | neverretire.ru ✅ | ✅ | книга/PDF, YT — ⬜ | **P0** |
| **Gdepar** | ✅ | gdepar.ru ✅ | ✅ | B2B лиды MVP ✅ | **P0** |
| **Stern** | ✅ | — | ✅ | tripwire 390₽ 🔒 | P1 |
| **Garden** | ✅ | — | ✅ curated | PDF 290₽ ⬜ | P1 |
| **Lenin** | ✅ | — | ✅ | Stars/donate ✅ | P2 |
| **HA / дом** | notify | — | — | — | P1 infra |

---

## 3. ТЗ не начато / отложено (приоритет)

### P0 — сделать первым (2–4 недели)

| # | Задача | Почему | Артефакт |
|---|--------|--------|----------|
| 1 | **Yandex Metrika** оба сайта | KPI слепые, воронка | `docs/metrika_goals_setup.md` |
| 2 | **Pension:** финал книги + yt-001 + `/buy` | главный revenue | `pension_book_publish_tz.md` |
| 3 | **Gdepar:** LLM_PCT решение через 2–4 нед | cost/quality | `GDEPAR_ASSISTANT_LLM_PCT` |
| 4 | **KPI недели** автоматом | `empire_weekly_posting_metrics.py` → JSON | `data/empire_weekly_kpi.json` |
| 5 | **Router watchdog** | VPN/торрент без ваших запросов | `empire-router-watchdog.timer` |

### P1 — можно через 1–2 месяца

| # | Задача |
|---|--------|
| 6 | VK/Дзен адаптеры omni-publish (`TZ_FINAL` §3) |
| 7 | Stern tripwire YooKassa live (после 3 видео) |
| 8 | Garden PDF + ВК оформление |
| 9 | Spy video → shorts_scripts |
| 10 | Uptime Kuma / Netdata (если digest не хватает) |

### P2 — ждёт триггеров (`TZ_FINAL` §10)

| # | Задача | Триггер |
|---|--------|---------|
| 11 | PostgreSQL | SQLite > 1 GB |
| 12 | Redis + worker scale | queue backlog |
| 13 | Отдельный VPS для VPN | частые падения сайта из-за VPN |
| 14 | Нейрокомментинг | после P0 + отдельное включение |
| 15 | GPU / локальный ПК | RAM > 7 GB неделю |

---

## 4. Финансы и unit economics

### 4.1. Текущие расходы (факт/ориентир)

| Статья | ₽/мес | Обязательность |
|--------|-------|----------------|
| VPS Austria 4/8/120 | **2 400** | да |
| Домены (амортизация) | 300 | да |
| Cursor | 1 500 | да (разработка) |
| OpenRouter | 500–1 500 | по usage |
| fal.ai | 0–300 | опционально |
| **Итого минимум** | **~4 700–5 000** | |
| **Рабочий режим** | **~7 000** | + proxy/S3 при Spy |

**Доходы сейчас:** 0 ₽.

### 4.2. Unit economics по продуктам

| Продукт | Цена | CAC max | LTV target | Break-even |
|---------|------|---------|------------|------------|
| Stern tripwire | 390 ₽ | 150 ₽ | 1 200 ₽ | ~13 продаж/мес покрывают VPS |
| Garden PDF | 290 ₽ | 100 ₽ | 800 ₽ | ~17 продаж/мес |
| Pension книга | TBD ~490 ₽ | 200 ₽ | 2 000 ₽ | 10 продаж/мес → 4 900 ₽ |
| Gdepar B2B lead | 500 ₽/лид | — | — | 5 лидов/мес → 2 500 ₽ |
| Lenin Stars | var | 0 | — | прогрев |

**Правило:** расходы Empire > 6 000 ₽/мес **2 месяца подряд** без выручки → стоп реклама, ревизия LLM.

### 4.3. Прогноз доходов (консервативный)

| Период | Ориентир ₽ | Условие |
|--------|------------|---------|
| 2026 Q3 | 0 | pre-launch |
| 2026 Q4 | 48 000 | Stern+Garden+Pension PDF launch |
| 2027 H1 | 300 000 | YT Pension + gdepar premium |

Ledger-шаблон: `docs/empire_business_plan_2026.md` §4 → `data/empire_finance_ledger.json` (создать вручную или из дашборда).

---

## 5. Инфра: что задеплоено 2026-07-15

| Компонент | Расписание | Действие |
|-----------|------------|----------|
| `empire-router-watchdog` | каждые 30 мин | check + auto-fix Flint |
| `empire-morning-brief` | 07:05 MSK | короткий TG: VPS+роутер+постинг |
| `empire-weekly-posting-metrics` | вс 08:30 MSK | KPI постинга → JSON |
| `empire-daily-audit` | 07:00 MSK | без изменений |
| `empire-diagnostics-watchdog` | каждые 2 ч | + router state в digest |

**Безопасность:** bootstrap :8789 **не меняли** (recovery с роутера). reverse SSH уже restricted в authorized_keys.

---

## 6. Еженедельная оценка постинга

Метрики (`scripts/empire_weekly_posting_metrics.py`):

- `tg_posts_published`, `autopost_failures`, `success_rate` по персонам
- очередь `post_drafts` pending
- `efficiency_notes` — автоматические рекомендации

Пороги: `docs/empire_kpi_sheets_template.md`, `docs/audit/14_PIPELINE_R5_AUTOPOST.md`.

---

## 7. Следующий шаг владельца (единственный блокер)

1. Создать счётчики **Yandex Metrika** (gdepar + neverretire) — без этого ROI постинга не измерить.

Остальное — автоматизировано на VPS.
