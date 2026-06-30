# Контрольные точки gdepar (ИИ-помощник и смежное)

Фиксация состояния без ожидания подтверждений. Git в проекте может отсутствовать — ориентир по дате и `GDEPAR_ASSET_VERSION`.

## CP-20260520 — ТЗ без участия владельца (кроме Метрики)

**Сделано:**

- Помощник «Пар?»: заглушка, LLM 25%, кэш, RL, RAG, стриминг SSE (`/api/gdepar/assistant/stream`).
- Саммари попапа: LLM 100% при наличии `OPENROUTER_API_KEY`.
- Виджет: z-index над картой, подпись «Помощник», cookie `gdepar_asst_sid`, логи `timing` + `session_id`.
- Health: `GET /api/gdepar/health` — флаги assistant/popup_summary/metrika.
- Документация: ТЗ §7 решения, `metrika_goals_setup.md`, nginx stream без буферизации.
- Тесты: `pytest tests/` (59+), деплой `scripts/deploy_gdepar.sh`.

**Ждёт владельца:**

- `YANDEX_METRIKA_ID` и создание JS-целей в кабинете Метрики.
- Чеклист напоминаний: **`docs/REMINDERS_gdepar.md`** (4 пункта + мастер-ТЗ).

**Вне репозитория:**

- p95-алерты в Grafana/хостинге (смотреть `journalctl -u empire_gdepar | grep timing`).

**Проверка после выката:**

```bash
curl -s http://127.0.0.1:8001/api/gdepar/health | python3 -m json.tool
curl -sS -X POST http://127.0.0.1:8001/api/gdepar/assistant/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"баня","page":"home"}' | head
```

`GDEPAR_ASSET_VERSION=20260520b`

## CP-20260621 — B2B MVP + OSM EUROPE_RU

**Сделано:**

- MVP-схема БД: `tools/banya_schema_mvp.py` — цены, вместимость, `banya_leads`, `banya_owner_accounts`, `seo_landings`.
- Лиды: `POST /api/banya/lead` (phone_reveal, whatsapp, booking_request, map_click); телефон скрыт в API до клика.
- UI: `static/gdepar/lead.js` — «Показать телефон» на карте и карточке бани.
- B2B: `/partners` + ссылка в навигации.
- Регионы до Урала: `EUROPE_RU` — 56 областей в `tools/banya_regions.py`.
- Парсинг: `./scripts/run_osm_europe_ru.sh` → `logs/osm_europe_ru.log` (retry Overpass 429, зеркало kumi).

**Следующий шаг (не блокер):**

- После OSM: `yandex_scrape.py enrich` по MO, MSK, SPB.
- Owner dashboard, premium-сортировка, SEO-лендинги — по мастер-ТЗ.

**Проверка:**

```bash
tail -f logs/osm_europe_ru.log
curl -s http://127.0.0.1:8001/partners | head
curl -sS -X POST http://127.0.0.1:8001/api/banya/lead \
  -H 'Content-Type: application/json' \
  -d '{"spot_id":1,"lead_type":"phone_reveal","source":"test"}' | python3 -m json.tool
```
