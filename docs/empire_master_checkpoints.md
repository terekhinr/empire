# Контрольные точки — мастер-ТЗ (OMNI EMPIRE FINAL)

| ID | Дата | Что сделано |
|----|------|-------------|
| CP-EM-001 | 2026-05-20 | gdepar AI + деплой (отдельное ТЗ) |
| CP-EM-002 | 2026-05-20 | Автономный каркас: unit-файлы, бэкап, publications/jobs, publish adapters, worker, analytics.db, dashboard ops |
| CP-EM-003 | 2026-05-20 | Реализовано: `Publication`/`Job`, `empire_publish.py`, `empire_worker.py`, `analytics_db.py`, `empire_flags.py`, media GC, RSS → neverretire.ru, dashboard (мультиканал + стопы + systemctl), 7 тестов |
| CP-EM-004 | 2026-05-20 | Фаза 1 каркас: `news`, `spy_signals`, `neurocomment_plans`, `shorts_scripts`; news/spy/neuro/shorts jobs; дашборд 10 вкладок; pipeline прогнан (60 news, 40 spy, 5 neuro, 5 scripts); бани **≥200 published**; deploy_empire_infra OK; **71 pytest** |
| CP-EM-005 | 2026-05-20 | spy→draft (`spy_to_draft.py`, `/spy`, дашборд), `empire_sales` :8002, `pii_validator`, `scout_yt`, `weekly_insights`, `scripts/autonomous_tick.sh`, **73 pytest** |
| CP-EM-006 | 2026-05-15 | `empire_sales`+`empire_worker` active; cron `/etc/cron.d/empire-autonomous` (каждые 2ч); tick: +25 news, +40 spy, draft **#221** из разведки; insights `data/insights/insights_2026-05-15.json` |
| CP-EM-007 | 2026-05-15 | Фаза 4 каркас: `sales.db` products/course_users/entitlements, `empire_stern_bot` (lead+дисклеймер), `data/stern_products.json`, nginx `pay_neverretire.conf`, бэклог |

## После возвращения (≈5 мин, без Run в чате)

```bash
cd /root/projects/empire
EMPIRE_SKIP_EMBEDDINGS=1 ./venv/bin/pytest tests/ -q
sudo ./scripts/deploy_empire_infra.sh   # unit-ы + cron бэкапа
sudo systemctl start empire_worker      # если ещё не запущен
```

Опционально пересобрать RSS: `python3 -c "import asyncio; from rss_maker import generate_zen_rss; asyncio.run(generate_zen_rss())"`.

**Нужно только от вас (не блокирует код):** VK/VC/MAX/Telethon токены, Metrika ID на gdepar, `YANDEX_METRIKA_ID` в env.
