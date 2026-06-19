# Home Assistant на Armbian (Docker) — сеть и Telegram

Схема: **Armbian → Docker → Home Assistant** (`192.168.1.41:8123`).

## У вас: Home Assistant **Supervised** (Supervisor)

По `docker ps`: `hassio_supervisor`, `homeassistant`, дополнения `tailscale`, `esphome`, `ssh`.

- Файла **`docker-compose.yml` нет** — это нормально, всем управляет Supervisor.
- **`network_mode: host` для HA не делаем** — сломает Supervised.

**Решение:** мост `ha_telegram_bridge.py` на **хосте armbian** (вне Docker), HA ходит на `http://192.168.1.41:8766/notify`.

## Почему Telegram из HA не работает напрямую

Контейнер HA **не видит** Tailscale и часто **не видит** `api.telegram.org` (timeout).  
Мост на VPS (`100.84.19.35:8766`) с HA-контейнера тоже **timeout**.

## Шаг 1. Зайти на Armbian (не Terminal в HA)

С ПК в той же сети:

```bash
ssh root@192.168.1.41
```

(или `ssh armbian@192.168.1.41` — как настраивали)

Здесь должно работать:

```bash
sudo docker ps
```

---

## Шаг 2. Найти, как запущен HA

```bash
sudo docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"
```

Запомните **NAME** (например `homeassistant`).

Узнать, есть ли compose:

```bash
sudo docker inspect homeassistant --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'
```

Если пусто — контейнер через `docker run`, ищите скрипт:

```bash
grep -r "home-assistant" /root /home 2>/dev/null | head -20
ls -la /root/*/docker-compose.yml /opt/*/docker-compose.yml 2>/dev/null
```

---

## Шаг 3A. Если есть `docker-compose.yml`

Откройте файл (путь из шага 2), в сервис `homeassistant` добавьте:

```yaml
    network_mode: host
```

Уберите секцию `ports:` (при host-сети не нужна).  
HA откроется на **8123** хоста: `http://192.168.1.41:8123`.

Перезапуск:

```bash
cd /путь/к/папке/compose
sudo docker compose down
sudo docker compose up -d
```

В HA `secrets.yaml`:

```yaml
ha_notify_url: "http://100.84.19.35:8766/notify"
ha_notify_token: "Bearer ВАШ_HA_NOTIFY_TOKEN"
```

(`HA_NOTIFY_TOKEN` — в `.env` на VPS empire)

---

## Шаг 3B. Если compose нет — только `docker run`

Посмотреть, как создан контейнер:

```bash
sudo docker inspect homeassistant --format '{{.Config.Image}}'
sudo docker inspect homeassistant --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

Остановить и пересоздать **с host-сетью** (подставьте свой путь `/config`):

```bash
sudo docker stop homeassistant
sudo docker rm homeassistant

sudo docker run -d \
  --name homeassistant \
  --restart unless-stopped \
  --network host \
  -v /ПУТЬ/К/config:/config \
  -e TZ=Europe/Moscow \
  ghcr.io/home-assistant/home-assistant:stable
```

`/ПУТЬ/К/config` — каталог, где лежат `configuration.yaml` и `packages/` (тот же, что в File editor).

---

## Шаг 3C. Мост на Armbian (если host network не хотите)

На **armbian** (хост):

```bash
cd /root
# скопировать ha_telegram_bridge.py и .env с TELEGRAM_TOKEN, ADMIN_ID, HA_NOTIFY_TOKEN
pip3 install aiohttp aiogram python-dotenv
python3 ha_telegram_bridge.py
```

В HA `secrets.yaml`:

```yaml
ha_notify_url: "http://172.17.0.1:8766/notify"
ha_notify_token: "Bearer тот_же_секрет"
```

Если timeout — попробуйте `http://192.168.1.41:8766/notify`.

---

## Шаг 4. Проверка

На armbian:

```bash
curl -s http://100.84.19.35:8766/health
```

После `network_mode: host` должно быть `{"ok":true}`.

В HA: **Сценарии → Empire — тест Telegram**.

---

## Tailscale на armbian

Для варианта 3A нужен Tailscale на **хосте** armbian (у вас уже есть в меню HA — проверьте, что служба на хосте: `tailscale status` в SSH).
