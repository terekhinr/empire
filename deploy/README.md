# Деплой gdepar.ru

## Архитектура

| Компонент | Путь / порт |
|-----------|-------------|
| Приложение | `gdepar_app.py` → `127.0.0.1:8001` (uvicorn) |
| systemd | `empire_gdepar.service` |
| Nginx | `deploy/nginx/empire_hub` → `gdepar.ru`, зеркало `гдепар.рф` |
| БД | `empire.db` (SQLite), `DATABASE_URL` в `.env` |
| Статика | `/static/` — отдаёт Nginx |

## Первичная настройка (один раз)

```bash
cd /root/projects/empire
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt

# Секреты (не в git)
cp .env.example .env   # заполнить OPENROUTER_API_KEY, BANYA_ADMIN_TOKEN и т.д.

sudo mkdir -p /etc/empire
sudo cp deploy/gdepar.production.env.example /etc/empire/gdepar.env
sudo chmod 600 /etc/empire/gdepar.env
# В /etc/empire/gdepar.env: YANDEX_METRIKA_ID, при необходимости GDEPAR_ASSISTANT_LLM=1
```

## Выкат после изменений кода

```bash
cd /root/projects/empire
sudo ./scripts/deploy_gdepar.sh
```

Скрипт: `pytest` → копирует unit и nginx → `restart empire_gdepar` → `reload nginx` → `GET /api/gdepar/health`.

## Проверки

```bash
systemctl status empire_gdepar --no-pager
curl -s http://127.0.0.1:8001/api/gdepar/health
curl -sI https://gdepar.ru/ | head
curl -sI https://gdepar.ru/api/gdepar/health
```

## Включение LLM на проде

**Текущее продуктовое решение (ТЗ §7):** помощник — `GDEPAR_ASSISTANT_LLM=1`, **`GDEPAR_ASSISTANT_LLM_PCT=25`**; саммари — **`GDEPAR_POPUP_SUMMARY_LLM=1`**, `GDEPAR_POPUP_SUMMARY_LLM_PCT=100`. Отзывы в промпте LLM разрешены.

Файл `/etc/empire/gdepar.env` (шаблон `deploy/gdepar.production.env.example`). Нужен `OPENROUTER_API_KEY` в `.env`.

После правок: `sudo systemctl restart empire_gdepar`.

Проверка rollout (в JSON ответа `llm_rollout`, `llm`, `stub`):

```bash
curl -sS -X POST http://127.0.0.1:8001/api/gdepar/assistant \
  -H 'Content-Type: application/json' \
  -d '{"message":"баня в Химках","page":"map"}' | python3 -m json.tool
```

## Метрика

`YANDEX_METRIKA_ID=<цифры>` в env. Пошагово: **`docs/metrika_goals_setup.md`**. События в коде уже есть.

## Логи

```bash
journalctl -u empire_gdepar -f
```

Фильтр помощника: `journalctl -u empire_gdepar | grep gdepar.assistant`  
Латентность (p95 вручную): `journalctl -u empire_gdepar | grep 'timing route='`

## Контрольные точки

`docs/gdepar_checkpoints.md` — что выкатано и что ждёт только Metrika ID.

---

# Деплой ядра империи (мастер-ТЗ)

| Unit | Процесс | Порт |
|------|---------|------|
| `empire_main` | `main.py` (бот + scheduler) | — |
| `empire_worker` | `empire_worker.py` (jobs) | — |
| `empire_webapp` | `web_app.py` | 8000 |
| `empire_dashboard` | `dashboard.py` (Streamlit) | 8501 |
| `empire_sales` | `empire_sales.py` (webhook stub) | 8002 |

```bash
cd /root/projects/empire
sudo ./scripts/deploy_empire_infra.sh
sudo systemctl start empire_main empire_worker empire_webapp empire_dashboard
```

Бэкап SQLite (cron 03:15 UTC): `scripts/backup_empire_db.sh` → `/var/backups/empire/`.

Контрольные точки: `docs/empire_master_checkpoints.md`.

## Дашборд из интернета

**https://hub.neverretire.ru** — nginx + basic auth → Streamlit :8501.

Пошагово: `docs/dashboard_external_access.md`.
