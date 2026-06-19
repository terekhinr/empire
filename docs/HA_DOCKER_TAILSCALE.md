# HA в Docker не видит Tailscale (timeout на мост)

## Симптом

- Мост на VPS работает (`curl` с VPS → Telegram ✅)
- Сценарий HA: **timeout** на `rest_command.empire_telegram`
- Раньше: timeout на `api.telegram.org`

## Причина

Home Assistant в **Docker** использует сеть контейнера. **Tailscale** обычно на **хосте** (armbian), маршруты `100.x.x.x` в контейнер **не попадают**.

## Проверка

В дополнении **Terminal** (если оно в том же Docker, что HA):

```bash
curl -m 5 http://100.84.19.35:8766/health
```

Если **нет ответа** — нужен один из вариантов ниже.

---

## Вариант A — `network_mode: host` (проще всего)

В `docker-compose.yml` сервиса homeassistant:

```yaml
services:
  homeassistant:
    network_mode: host
    # ... остальное без ports: 8123:8123
```

Пересоздать контейнер. Тогда HA использует сеть хоста + Tailscale.

`secrets.yaml`:

```yaml
ha_notify_url: "http://100.84.19.35:8766/notify"
ha_notify_token: "Bearer ВАШ_HA_NOTIFY_TOKEN"
```

---

## Вариант B — мост на armbian (localhost)

1. Скопировать на armbian: `ha_telegram_bridge.py`, `.env` с `TELEGRAM_TOKEN`, `ADMIN_ID`, `HA_NOTIFY_TOKEN`.
2. Запустить на armbian: `python3 ha_telegram_bridge.py` (порт 8766).
3. В HA `secrets.yaml`:

```yaml
ha_notify_url: "http://172.17.0.1:8766/notify"
```

(или `http://host.docker.internal:8766/notify` — зависит от Docker)

`ha_notify_token` — тот же Bearer-секрет.

---

## Вариант C — только empire-бот

Пока не починена сеть: уведомления вручную/через бота; автоматизации HA без Telegram.
