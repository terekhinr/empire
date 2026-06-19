# Бэклог мастер-ТЗ — статус на 2026-05

Легенда: ✅ готово / каркас · 🟡 частично · ⬜ не начато · 🔑 нужны ключи/контент

## Фаза 0 — гигиена

| Пункт | Статус |
|-------|--------|
| WAL SQLite | ✅ |
| Бэкап cron | ✅ |
| cgroups unit-ы | ✅ |
| neverretire без OOM (`empire_models`) | ✅ |

## Фаза 1 — публикация + UGC

| Пункт | Статус |
|-------|--------|
| publications + empire_publish | ✅ |
| dzen_rss → neverretire.ru | ✅ |
| vk / vc / max адаптеры | 🟡 заглушки |
| news + spy + neuro dry-run | ✅ |
| shorts_scripts | ✅ |
| dashboard 10 вкладок | ✅ |
| spy → draft | ✅ |
| ≥200 бань published | ✅ |
| Telethon spy реальный | ⬜ 🔑 |
| Нейрокомментинг live | ⬜ фаза 2 |

## Фаза 3 — аналитика

| Пункт | Статус |
|-------|--------|
| analytics.db схема | ✅ |
| source_id / deeplink | ✅ |
| daily_subs snapshot | 🟡 placeholder |
| AI Insights Claude | 🟡 stub JSON |
| 14 дней без пропусков | ⬜ |

## Фаза 4 — «Железная спина»

| Пункт | Статус |
|-------|--------|
| sales.db products/entitlements | ✅ CP-EM-007 |
| empire_sales :8002 | ✅ |
| pay.neverretire.ru nginx | 🟡 conf готов, нужен DNS+LE |
| empire_stern_bot lead+дисклеймер | ✅ код, 🔑 `STERN_BOT_TOKEN` |
| YooKassa create payment | ⬜ 🔑 |
| 3 урока tripwire сняты | ⬜ контент |
| Оплата 390 ₽ включена | ⬜ после контента |

## Фаза 5 — Shorts

| Пункт | Статус |
|-------|--------|
| script_factory + dashboard | ✅ |
| yt_trends API | 🟡 stub JSON |

## Качество контента (P0)

| Пункт | Статус |
|-------|--------|
| gdepar анти-повторы (полки/тишина) | 🟡 усилить Q2 |
| stern превью фото+текст | ⬜ Q1 |
| pension raw_news + выбор новостей | ⬜ Q3–Q5 |
| spy_inspired в расписании | ⬜ Q6 |

См. `docs/empire_content_quality_backlog.md`, план `docs/empire_master_plan_rf_2026.md`.

## Дистрибуция РФ (без VPN)

| Пункт | Статус |
|-------|--------|
| Мастер-план §14 FINAL | ✅ |
| Garden ВК+Дзен вручную | ⬜ заказчик |
| vk_wall live | ⬜ 🔑 |
| lenin ВК+Дзен | ⬜ |

## Вне скоупа сейчас

- garden: мерч, % заказов бань (не YooKassa-гайды)
- gdepar Metrika | 🔑
- Видео-рендер, GPU
- Нейрокомментинг live до Spy+ревью dry-run

Контрольные точки: `empire_master_checkpoints.md`.
