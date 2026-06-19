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
