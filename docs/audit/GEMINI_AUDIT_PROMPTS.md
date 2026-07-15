# Промпты для Gemini · аудит Empire (инфра + проекты + финансы)

Скопируйте блок целиком в [Gemini](https://gemini.google.com). Приложите файлы: `docs/infra/ARCHITECTURE.md`, `docs/EMPIRE_PIPELINE_CHECKLIST.md`, `docs/empire_business_plan_2026.md`, `docs/TZ_OMNI_MEDIA_EMPIRE_FINAL.md`, `docs/audit/2026-07-15_FULL_INFRA_AUDIT.md`.

---

## Промпт 1 — Полный аудит инфраструктуры

```
Ты senior DevOps и системный архитектор. Проанализируй приложенную документацию Empire (VPS в Австрии + домашний роутер Flint OpenWrt + Home Assistant).

Задачи:
1. Нарисуй текстовую схему потоков данных (сайты, TG-боты, VPN podkop/zapret/Amnezia, бэкапы Я.Диск).
2. Список single points of failure и как их снизить БЕЗ второго VPS (если возможно).
3. Чеклист «ничего не сломать» перед любым hardening (порты 8789, 6223, Tailscale).
4. Топ-5 оптимизаций RAM/CPU на VPS 4vCPU/8GB — с оценкой экономии в MB и риском.
5. Сравни текущий мониторинг (daily-audit, watchdog, router-watchdog) с best practice для solo-founder.

Формат: таблицы + numbered list. Язык: русский. Без воды.
```

---

## Промпт 2 — Аудит проектов и приоритетов

```
Контекст: медиа-империя из 5 TG-персон (Pension, Gdepar, Stern, Garden, Lenin), 2 сайта, автопост, SQLite, Streamlit dashboard.

По EMPIRE_PIPELINE_CHECKLIST и TZ_OMNI_MEDIA_EMPIRE_FINAL:
1. Сгруппируй задачи в P0 / P1 / P2 с обоснованием impact vs effort (матрица 2×2).
2. Что блокирует монетизацию прямо сейчас?
3. Какие «новые ТЗ» из FINAL ещё не начаты — оцени каждое в story points (1–8).
4. Рекомендуемый порядок на 4 недели при 10 ч/нед на Empire.

Учти: доходов пока нет, Metrika не подключена, автопост 5 TG уже работает.
```

---

## Промпт 3 — Финмодель и unit economics

```
По empire_business_plan_2026.md и channel_monetization.md построй:

1. P&L на 12 месяцев (расходы: VPS 2400, Cursor 1500, OpenRouter 500-1500, домены 300; доходы: Stern 390, Garden 290, Pension book TBD, gdepar B2B leads).
2. Unit economics: CAC, LTV, break-even units/month для каждого продукта.
3. Сценарии: pessimistic / base / optimistic для Q4 2026 и H1 2027.
4. При каком MRR имеет смысл НПД vs ИП?
5. Триггеры «стоп расходов» если выручка = 0 ещё 3 месяца.

Вывод: одна таблица «месяц | расход | доход | накопительный cashflow».
Валюта: RUB. Консервативные допущения явно пометь.
```

---

## Промпт 4 — Эффективность постинга (еженедельный ритуал)

```
Данные за неделю (вставь вывод scripts/empire_weekly_posting_metrics.py или journalctl):

[PASTE: tg_posts_published, autopost_failures, by_persona, queue_pending]

Оцени:
1. Success rate автопоста — норма или проблема?
2. Какие персоны недокормлены контентом (queue < 3)?
3. Рекомендации по частоте слотов (не увеличивать >5/день без A/B).
4. Связь с Metrika (если нет — что измерять вручную).
5. Одно решение на следующую неделю (1 предложение).

Формат: 10 строк максимум + emoji статус.
```

---

## Промпт 5 — Роутер Flint (VPN/podkop/zapret/torrent)

```
Домашняя сеть: GL-MT6000 Flint 2, OpenWrt 24.10, podkop+sing-box → VPS VLESS, zapret2, awg0 Amnezia, Transmission, Samba USB.

Лог router-watchdog (вставь last_summary из /var/log/empire/router-state.json):

[PASTE]

1. Диагностика: что сломано и почему (DNS nftset, awg handshake, USB mount).
2. Безопасный порядок remediation (restart podkop → zapret → awg → fix-all.sh).
3. Когда НЕ запускать fix-all (чтобы не сбросить рабочие настройки).
4. Чеклист ручной проверки с ПК: YouTube, Telegram, Gemini, Samba Z:

Язык: русский. Кратко.
```

---

## Промпт 6 — Ежемесячный re-audit (повторять)

```
Проведи повторный аудит Empire как в промптах 1–3. Дата: [DATE].

Изменения с прошлого месяца:
- [вставь diff статусов из EMPIRE_PIPELINE_CHECKLIST]
- [вставь empire_weekly_kpi.json последние 4 недели]
- [расходы OpenRouter/Cursor факт]

Вывод: 3 wins, 3 risks, 3 actions на следующий месяц.
```
