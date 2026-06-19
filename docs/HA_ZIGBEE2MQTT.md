# Zigbee2MQTT + Home Assistant (Supervised / Docker)

> **Решение empire (май 2026): остаёмся на ZHA.** Zigbee2MQTT **не устанавливать**. Этот файл — справка, если когда-нибудь понадобится миграция.

**Ваш сервер:** armbian, **Home Assistant Supervised** (`hassio_supervisor` + контейнер `homeassistant`).  
**Координатор:** Sonoff Zigbee 3.0 USB Dongle **Plus V2** (ZBDongle-E).

---

## ⚠️ Важно: ZHA или Zigbee2MQTT — не оба сразу

Сейчас в проекте по ТЗ используется **ZHA** (интеграция в HA, `zigbee.db`).

| | ZHA | Zigbee2MQTT |
|---|-----|-------------|
| Один USB-стик | ✅ уже занят ZHA | нужен **свободный** стик |
| Одновременно на одном стике | ❌ | ❌ |
| Переход на Z2M | удалить ZHA, прошить/перепривязать **все** устройства заново | |

**Рекомендация:** если реле/протечка уже в **ZHA** — **оставайтесь на ZHA**. Z2M имеет смысл, если сознательно переходите (больше гайдов в сообществе, MQTT, Zigbee2MQTT UI).

Ниже — как поднять Z2M, если вы **переходите** или ставите **второй** координатор.

---

## Вариант A — дополнение Supervisor (ваш случай)

Не ставят Z2M **внутрь** контейнера `homeassistant`. Ставят **отдельное дополнение** (свой контейнер) + **Mosquitto**.

### A1. Mosquitto (MQTT)

1. **Настройки** → **Дополнения** → **Установить магазин дополнений** (если пусто).
2. **Mosquitto broker** → **Установить** → **Запустить** → **Автозапуск**.
3. **Учётная запись** (опционально): вкладка **Пользователи** — логин/пароль для MQTT.

Запомнить:
- Хост для других дополнений: `core-mosquitto` или `a0d7b954-mosquitto` (имя из списка дополнений).
- Порт: `1883`.

### A2. Репозиторий Zigbee2MQTT

1. **Дополнения** → **Дополнения** → **⋮** → **Репозитории**.
2. Добавить: `https://github.com/zigbee2mqtt/hassio-zigbee2mqtt`
3. **Обновить** список.

### A3. Установить дополнение Zigbee2MQTT

1. **Zigbee2MQTT** → **Установить**.
2. Не запускать, пока не настроен конфиг.

### A4. USB-координатор на armbian (SSH)

На **armbian** (не в Terminal HA без docker):

```bash
ls -l /dev/serial/by-id/
```

Пример для Plus V2:

```
usb-ITEAD_SONOFF_Zigbee_3.0_USB_Dongle_Plus_V2_...-if00 -> ../../ttyUSB0
```

Скопировать **полный путь** `/dev/serial/by-id/usb-ITEAD_...-if00`.

**Если стик занят ZHA:** остановите HA или удалите интеграцию ZHA, иначе порт busy.

```bash
# кто держит порт
sudo lsof /dev/ttyUSB0 2>/dev/null || sudo fuser -v /dev/ttyUSB0
```

### A5. Конфигурация дополнения Zigbee2MQTT

**Конфигурация** дополнения (YAML). Пример для **Plus V2** (чип EFR32, адаптер **ember**):

```yaml
data_path: /config/zigbee2mqtt
homeassistant: true
permit_join: false
mqtt:
  base_topic: zigbee2mqtt
  server: mqtt://core-mosquitto:1883
  # user: ваш_логин
  # password: ваш_пароль
serial:
  port: /dev/ttyUSB0
  adapter: ember
advanced:
  log_level: info
```

Новые версии аддона могут требовать:

```yaml
data_path: /addon_config/zigbee2mqtt
```

— смотрите подсказку в логе дополнения при ошибке `data_path option is missing`.

**Устройство USB в дополнении:** в интерфейсе Supervisor часто есть поле **Device** — выбрать Sonoff dongle. Если нет — в конфиге только `port` как выше; на некоторых хостах нужно:

```yaml
# в настройках дополнения (не в configuration.yaml HA)
devices:
  - /dev/serial/by-id/usb-ITEAD_SONOFF_Zigbee_3.0_USB_Dongle_Plus_V2_XXXXX-if00:/dev/ttyUSB0
```

(точный синтаксис зависит от версии аддона — см. документацию репозитория hassio-zigbee2mqtt).

**Запуск** → **Журнал** — должно быть `Started zigbee-herdsman` / `Zigbee2MQTT started`.

### A6. Home Assistant ↔ MQTT

1. **Настройки** → **Устройства** → **Добавить интеграцию** → **MQTT**.
2. Брокер: тот же Mosquitto (`core-mosquitto`, порт 1883).
3. При `homeassistant: true` в Z2M устройства часто появляются **сами** (MQTT discovery).
4. Иначе: **MQTT** → **Настроить** → подписка на `zigbee2mqtt/#`.

Проверка: **Инструменты разработчика** → **MQTT** → подписаться на `zigbee2mqtt/bridge/state` → должно быть `online`.

### A7. Пейринг

1. Веб-интерфейс Z2M: ссылка в **Информация** дополнения (порт 8099) или через ingress.
2. **Permit join** ON (или кнопка в UI).
3. Включить датчик/реле в режим сопряжения.
4. Назначить **area** в HA.

---

## Вариант B — отдельный Docker на armbian (без дополнения)

Если Supervisor не даёт USB — на **хосте** armbian:

```yaml
# /opt/zigbee2mqtt/docker-compose.yml (пример)
services:
  mosquitto:
    image: eclipse-mosquitto:2
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
    ports:
      - "1883:1883"
    restart: unless-stopped

  zigbee2mqtt:
    image: koenkk/zigbee2mqtt
    volumes:
      - ./data:/app/data
    devices:
      - /dev/serial/by-id/usb-ITEAD_SONOFF_Zigbee_3.0_USB_Dongle_Plus_V2_XXX-if00:/dev/ttyUSB0
    ports:
      - "8080:8080"
    environment:
      - TZ=Europe/Moscow
    restart: unless-stopped
```

`data/configuration.yaml` внутри volume:

```yaml
homeassistant: true
mqtt:
  server: mqtt://mosquitto:1883
serial:
  port: /dev/ttyUSB0
  adapter: ember
```

В HA: интеграция **MQTT** → брокер `192.168.1.41:1883` (IP **armbian**, не `127.0.0.1` из контейнера HA).

---

## Прошивка координатора Plus V2

Для **ember** иногда нужна актуальная прошивка MultiPAN — см. [Sonoff → Zigbee2MQTT](https://dongle.sonoff.tech/guide/zbdongle-p/connecting_to_zigbee2mqtt/).

Если в логе ошибки `ember` / `EZSP` — обновить прошивку через Sonoff docs или переключить `adapter` по таблице для вашей ревизии.

---

## Переход с ZHA на Z2M (кратко)

1. Записать список устройств в ZHA.  
2. **Настройки** → **ZHA** → **Удалить** интеграцию.  
3. Перезагрузка HA, убедиться что USB свободен.  
4. Установить Z2M (вариант A).  
5. **Все** Zigbee-устройства пепривязать (reset + permit join).  
6. `zigbee.db` ZHA больше не используется.

---

## Сравнение с вашим планом empire

| Задача | ZHA (сейчас) | Z2M |
|--------|--------------|-----|
| Реле, протечка, присутствие | ✅ уже в плане | заново |
| Локально без облака | ✅ | ✅ |
| Алиса через HA | ✅ | ✅ (через MQTT entities) |
| Сложность | ниже | MQTT + аддон |

---

## Чеклист

- [ ] Решение: остаться на ZHA или переход на Z2M  
- [ ] Mosquitto запущен  
- [ ] Репозиторий + дополнение Zigbee2MQTT  
- [ ] `ls /dev/serial/by-id/` — путь к dongle  
- [ ] `adapter: ember` для Plus V2  
- [ ] Z2M journal без ошибок  
- [ ] MQTT в HA, discovery  
- [ ] Permit join → первое устройство  

---

## Связанные файлы

- `docs/HA_PHASE2_ZHA_LOCALTUYA.md` — текущий план ZHA  
- `docs/HA_ARMBIAN_DOCKER.md` — сеть Supervised  
