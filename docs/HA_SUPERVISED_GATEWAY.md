# Supervised: HA не видит 192.168.1.41:8766

## Симптом

- На armbian: `curl http://127.0.0.1:8766/health` → **ok**
- В HA: timeout на `http://192.168.1.41:8766/notify`

Контейнер `homeassistant` в сети **hassio**, не на IP хоста.

## Шаг 1 — узнать шлюз (SSH armbian)

```bash
docker inspect homeassistant --format '{{range .NetworkSettings.Networks}}Gateway: {{.Gateway}}{{"\n"}}{{end}}'
```

Часто это **`172.30.32.1`** (у вас может отличаться).

## Шаг 2 — проверить с контейнера HA

```bash
docker exec homeassistant curl -s -m 5 http://172.30.32.1:8766/health
```

Если **ok** — в `secrets.yaml`:

```yaml
ha_notify_url: "http://172.30.32.1:8766/notify"
ha_notify_token: "Bearer ***REMOVED***"
```

Перезагрузить YAML → тест сценария.

## Если `/health` ok, а сценарий всё равно timeout

`health` — быстрый GET. Сценарий делает **POST /notify** → мост шлёт в Telegram. С armbian `api.telegram.org` часто **недоступен** — POST висит 20+ секунд.

Проверка с armbian (SSH):

```bash
curl -m 15 -X POST http://127.0.0.1:8766/notify \
  -H "Authorization: Bearer ВАШ_HA_NOTIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"test post"}'
```

Если висит — обновите мост и включите пересылку на VPS (Tailscale):

1. Скопировать `ha_telegram_bridge.py` в `/opt/empire-ha-bridge/`
2. В `/opt/empire-ha-bridge/.env` добавить:

```env
HA_NOTIFY_FORWARD_URL=http://100.84.19.35:8766/notify
HA_NOTIFY_FORWARD_ONLY=1
```

3. `systemctl restart empire-ha-bridge`
4. Повторить POST — ответ за 1–2 с, сообщение в Telegram.

Мост на VPS (`empire_ha_notify`) должен быть запущен.

## Шаг 3 — проверка из Terminal (дополнение HA)

```bash
curl -m 5 http://172.30.32.1:8766/health
curl -m 5 http://192.168.1.41:8766/health
```

Какой ответил `{"ok":true}` — тот URL в secrets.

## Шаг 4 — убедиться, что мост слушает все интерфейсы

На armbian:

```bash
ss -tlnp | grep 8766
systemctl status empire-ha-bridge
```

Должно быть `0.0.0.0:8766`.

## secrets.yaml — ещё

```yaml
telegram_chat_id: 497498662
```

**Без минуса** (если ещё `-497498662` — исправить).
