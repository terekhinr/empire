# Project OS — куда что класть (Empire + vault)

**Три слоя:** Obsidian (мышление) · git `docs/` (канон) · Око Саурона (цифры и ops).

Полный контекст: обсуждение «3 слоя» · мастер-план `docs/empire_master_plan_rf_2026.md`.

---

## 1. Правило inbox (раз в 2 недели, 15 мин)

**Inbox** = `Входящие/` в корне vault (не путать с `Empire/*/inbox/`).

| Вопрос | Куда |
|--------|------|
| Это пост в канал Empire? | `Empire/{persona}/inbox/` → когда готово → `queue/` |
| Это статья «навсегда» (инвестиции, референсы)? | `База знаний/{тема}/` |
| Это личная задача / быт? | `Life/tasks/inbox.md` или Tasks.org |
| Это **утверждённая** политика, ТЗ, чеклист для кода/VPS? | `docs/` в репозитории empire (git) |
| Это решение «делаем так»? | `docs/empire_decisions_YYYY-MM.md` + строка в review |
| Устаревший черновик ТЗ v2–v9? | `_archive/tz-superseded/` (не править) |
| Рецепт, fiction, разовая заметка? | `Life/` или `База знаний/` — или удалить |
| Не понятно за 30 сек | Оставить во `Входящие/` **не больше 2 недель** |

**Запрет:** токены ботов, API-ключи, пароли — только `.env` на VPS, **не** в Obsidian.

---

## 2. Еженедельный review (воскресенье, 30–45 мин)

### Порядок

1. **Око Саурона → P&L · Финансы → KPI недели** — заполнить форму (или обновить `data/empire_weekly_kpi.json`).
2. **Obsidian** — новая заметка из шаблона `_templates/weekly_project_review.md` → папка `_reviews/`.
3. Поле **«Решение недели»** в KPI (`notes`) = одна фраза из review (дублируется осмысленно).
4. Если решение меняет приоритеты — правка в `docs/empire_master_backlog.md` или `empire_decisions_*.md`.

### Шаблон и архив review

- Шаблон: `data/obsidian_vault/Empire/_templates/weekly_project_review.md`
- Готовые обзоры: `Empire/_reviews/YYYY-Www.md`
- **Ежедневный хаб Obsidian:** `Empire/00-СЕГОДНЯ.md` · пайплайн `00-ПАЙПЛАЙН.md` · индекс `00-ДОКУМЕНТАЦИЯ.md`
- **Sync docs/финансы:** `scripts/sync_empire_obsidian.py` → `Empire/_canon/`, `Empire/_finance/` · гайд `docs/obsidian_sync_empire_ru.md`

### Пороги «зелёный / красный»

`docs/empire_business_plan_2026.md` §6.2 — не выдумывать новые KPI без причины.

---

## 3. Карта папок vault

```text
Входящие/              ← быстрый сброс (с README-маршрутизацией)
_archive/              ← устаревшее, не удалять вслепую
Empire/
  _canvas/ _scenarios/ ← планирование, не импорт
  _templates/ _reviews/
  {persona}/inbox|queue|published/
Life/tasks/            ← личные дела (не синк на VPS)
База знаний/           ← статьи и референсы
```

Репозиторий:

```text
docs/          ← канон: ТЗ, планы, гайды, чеклисты
data/*.json    ← KPI, ledger (дашборд)
analytics.db   ← события (авто)
```

---

## 4. Канон ТЗ (единственный источник)

| Документ | Назначение |
|----------|------------|
| `docs/TZ_OMNI_MEDIA_EMPIRE_FINAL.md` | Мастер-ТЗ |
| `docs/empire_master_plan_rf_2026.md` | План дистрибуции РФ 2026 |
| `docs/empire_business_plan_2026.md` | P&L, KPI, монетизация |
| `docs/empire_master_backlog.md` | Статусы фаз |
| `docs/empire_decisions_2026-05.md` | Зафиксированные решения |

Старые версии v2–v9 — только в `_archive/tz-superseded/`.

---

## 5. Связанные документы

| Документ | Содержание |
|----------|------------|
| `docs/obsidian_practical_guide_ru.md` | Obsidian → Telegram |
| `docs/empire_obsidian_integration.md` | Импорт queue |
| `docs/empire_kpi_sheets_template.md` | Google Sheets (опционально) |
| `data/obsidian_vault/Empire/README.md` | Правила vault Empire |
