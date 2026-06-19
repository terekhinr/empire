# Spy + нейрокомментинг: чеклист запуска (Gdepar + Stern)

Связь: `docs/spy_setup_gdepar_stern.md`, `spy_config.py`, `data/spy_competitors.json`.

**Аккаунт:** SIM 3, [@nik2nik](https://t.me/nik2nik) (+79332766535) — только разведка, не pension.

---

## Текущий статус (флаги)

| Флаг | Значение | Смысл |
|------|----------|--------|
| `stop_spy` | **true** | live spy выключен |
| `stop_neurocomment` | **true** | neuro только dry-run в очереди, worker отменяет |
| `stop_worker` | false | worker работает |

Пока нет `.session` Telethon — spy **не включаем** (без `SPY_ALLOW_DRY_RUN`).

---

## Шаг 1 — API Telegram

1. [my.telegram.org](https://my.telegram.org) → API Development (можно на SIM 3)
2. В `/etc/empire/empire.env`:

```bash
TELETHON_API_ID=...
TELETHON_API_HASH=...
TELETHON_SESSION=/root/projects/empire/empire_spy_nik2nik
```

---

## Шаг 2 — Логин сессии (один раз)

На VPS (интерактивно, код из SMS на +79332766535):

```bash
cd /root/projects/empire
source venv/bin/activate
python scripts/telethon_login.py
```

Ожидаем: `OK: сессия ... user=nik2nik`

---

## Шаг 3 — Конкуренты

Проверить/дополнить `data/spy_competitors.json` (gdepar + stern каналы).

---

## Шаг 4 — Включить spy (live)

1. Дашборд → **Флаги** → `stop_spy` = **false**
2. Или `data/empire_flags.json`: `"stop_spy": false`
3. `systemctl restart empire_worker`

Ежедневный pipeline (`task_empire_daily_pipeline` в `main.py`):

- `news_ingest`
- `spy_dry_run` → при live Telethon станет реальным сбором (`telethon_spy.py`)
- `neurocomment_dry_run` — пока `stop_neurocomment=true`, job отменяется

Ручной прогон из дашборда: страница **Spy** → dry-run / spy→drafts.

---

## Шаг 5 — Нейрокомментинг (фаза 1: dry-run)

По ТЗ §4.3.3 — **7 дней ревью** планов в `neurocomment_plans` до live.

1. Оставить `stop_neurocomment: true`
2. Временно снять флаг → прогнать dry-run → снова включить stop
3. Дашборд → **Нейрокомментинг** — просмотр `dry_run` записей
4. Live (позже): отдельный аккаунт, лимит `NEUROCOMMENT_MAX_PER_HOUR=5`

---

## Шаг 6 — Мониторинг

```bash
journalctl -u empire_worker -f
journalctl -u empire_main -f | grep -E 'spy|neuro'
```

---

## Не путать

| Контур | Персоны |
|--------|---------|
| Spy + neuro | gdepar, stern |
| Автопост VK/Дзen | **pension** (`docs/pension_social_autopost.md`) |
| TG Empire approve | все персоны |
