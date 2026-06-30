# Шаблон Google Sheets · KPI Empire (§6.2)

**Назначение:** еженедельная сводка по всем линиям (сайты, соцсети, книга, расходы).  
**Дубли в дашборде:** вкладка **«P&L · Финансы»** → форма KPI + `data/empire_weekly_kpi.json`.

---

## 1. Быстрый старт

1. Скачайте CSV из дашборда: **P&L · Финансы** → кнопка **«Шаблон KPI CSV»**  
   или возьмите файл `templates/empire_weekly_kpi_template.csv` из репозитория.
2. [Google Таблицы](https://sheets.google.com) → **Файл → Импорт → Загрузка** → выберите CSV.
3. Разделитель: **запятая**. Кодировка: **UTF-8**.
4. Переименуйте лист: `KPI недели`.
5. Добавляйте **новую строку внизу** каждую неделю (не перезаписывайте шапку).

---

## 2. Колонки (что вносить)

| Колонка | Что писать | Зелёный ориентир |
|---------|------------|------------------|
| `week` | Дата понедельника ISO `2026-05-26` | — |
| `empire_ok` | `1` = без падений сервисов, `0` = были сбои | 1 |
| `cursor_spend_rub` | Подписка Cursor (Pro/Business) за неделю, ₽ | по вашему тарифу |
| `openrouter_spend_rub` | Расход OpenRouter за неделю ([activity](https://openrouter.ai/activity)) | ≤ 400 ₽/нед (~1 500/мес) |
| `fal_spend_rub` | fal.ai (Flux в дашборде/боте) за неделю | по факту генераций |
| `llm_spend_rub` | **Авто:** сумма трёх строк выше (можно не заполнять) | — |
| `garden_vk_subs` | Подписчики ВК Сад | рост |
| `gdepar_sessions` | Сессии gdepar.ru (Метрика) | рост |
| `stern_leads` | Новые лиды в боте | +5/мес |
| `pension_tg_subs` | TG Пенсия | +50/мес (фаза роста) |
| `pension_site_sessions` | Сессии neverretire.ru | ≥500/мес к launch |
| `pension_book_toc` | Визиты `/book` | рост |
| `pension_buy_clicks` | Цели buy/cta в Метрике | рост к launch |
| `tg_posts_published` | Постов в TG за неделю (все 5 каналов) | ≥70/нед при автопосте |
| `autopost_failures` | `[autopublish] skip` за неделю (`journalctl`) | **0** |
| `gift_emails` | Подписчиков `/gift` (накопительно) | **50** к 31.08 |
| `gdepar_phone_reveals` | `phone_reveal` / цель Метрики | рост с окт 26 |
| `orders` | Оплаченные заказы (шт) | по продукту |
| `revenue_rub` | Выручка за неделю | > 0 после launch |
| `expenses_rub` | Расходы Empire за неделю | ≤ ~1 500 + VPS/4 |
| `top_utm` | Лучший utm_source недели | не пусто при трафике |
| `notes` | Решение недели (1 фраза) | — |

Подробные пороги: `docs/empire_business_plan_2026.md` §6.2 · триггеры решений: `docs/audit/14_PIPELINE_R5_AUTOPOST.md` §4.

**Счётчики автопоста (bash):**

```bash
journalctl -u empire --since "7 days ago" | grep -c '\[autopublish\] published'
journalctl -u empire --since "7 days ago" | grep -c '\[autopublish\] skip'
```

---

## 3. Второй лист «P&L месяц» (опционально)

Импортируйте **P&L CSV** из дашборда (**Скачать P&L CSV**) на лист `P&L`.

Колонки: `month`, `expense_rub`, `income_sales_rub`, `income_total_rub`, `margin_rub`.

Формула контроля внизу:

```
=SUM(income_total_rub) - SUM(expense_rub)
```

должна совпадать с **Маржа YTD** в дашборде (с учётом периода).

---

## 4. Синхронизация с репозиторием

| Источник | Файл |
|----------|------|
| Расходы/доходы вручную | `data/empire_finance_ledger.json` |
| KPI недели (дашборд) | `data/empire_weekly_kpi.json` |
| Pension-only KPI | `data/pension_weekly_metrics.json` |
| Оплаты | `sales.db` |

Раз в месяц можно скопировать JSON в бэкап (rclone VPS-backup).

---

## 5. Pension — отдельная таблица

Для книги есть расширенная таблица в `pension_book_publish_tz.md` §6.5.  
Можно вести **второй лист** `Pension` с колонками: TG, VK, Dzen reads, YT views, …  
или использовать вкладку дашборда **«Pension · сводка»**.

---

*Импорт CSV обновляйте при добавлении колонок в `finance_ledger.KPI_COLUMNS`.*
