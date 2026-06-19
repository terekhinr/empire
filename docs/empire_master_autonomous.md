# Автономная работа по мастер-ТЗ (без участия владельца)

**Допущения (если не оспорено):**

- VK / MAX / VC.ru — **каркас адаптеров** без реальных API (нет токенов в `.env.example`).
- Telethon-Spy — **схема БД + dry-run заглушка**, без сессии `.session`.
- YooKassa / `empire_sales` — не трогаем (фаза 4).
- Парсеры бань — только если в `.env` уже есть ключи; иначе скрипт в worker с `skipped`.
- Деплой unit-ов на сервер — **скрипт готов**, `sudo ./scripts/deploy_empire_infra.sh` при возвращении.

**Нужно от вас позже (не блокирует код):** `VK_*`, Telethon API, подтверждение CF Email, Metrika ID.

Контрольные точки: `docs/empire_master_checkpoints.md`.

**Прогон pipeline вручную (без ожидания cron):**

```bash
cd /root/projects/empire
EMPIRE_SKIP_EMBEDDINGS=1 ./venv/bin/python scripts/run_phase1_pipeline.py
./venv/bin/python scripts/drain_jobs.py
```

**Автономный тик (cron каждые 2ч):**

```bash
# /etc/cron.d/empire-autonomous — пример:
# 10 */2 * * * root /root/projects/empire/scripts/autonomous_tick.sh >> /var/log/empire_autonomous.log 2>&1
./scripts/autonomous_tick.sh
```

**Бот:** `/spy` — список сигналов; `/spy draft 2` — черновики из разведки; `/spy one <id>` — один черновик.

**Сервисы:** `empire_sales` → `http://127.0.0.1:8002/health` (webhook YooKassa — заглушка).
