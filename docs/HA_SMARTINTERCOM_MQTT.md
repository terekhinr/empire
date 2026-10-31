# SmartIntercom → Home Assistant (MQTT)

Рекомендуемый путь: прошивка **BlueStreak** + локальный **Mosquitto** на HA.  
Облачный брокер **не нужен и не оплачивается**.

## Схема

```
SmartIntercom 192.168.1.101
        │ MQTT :1883
        ▼
Mosquitto addon (HA host 192.168.1.41)
        │
        ▼
Home Assistant (discovery homeassistant/#)
```

## Что уже поднято

| Компонент | Значение |
|-----------|----------|
| Addon | `core_mosquitto` (Mosquitto broker) |
| Порт | `192.168.1.41:1883` |
| Пользователь устройства | `smartintercom` |
| Пользователь HA | `homeassistant` |
| Пароли | `data/secrets/mqtt_*.pass` на VPS (не в git) |
| Интеграция HA | MQTT → `core-mosquitto`, discovery вкл. |
| Устройство | `server_type=MQTT`, retain=on |

## Сущности (discovery)

| Entity | Назначение |
|--------|------------|
| `binary_sensor.smartintercom_detektor_vyzova` | Идёт вызов |
| `sensor.smartintercom_status_linii` | Закрыто / Вызов / … |
| `switch.smartintercom_otkryt_dver` | Открыть дверь |
| `switch.smartintercom_otkryt_kureru` | Курьер |
| `switch.smartintercom_sbrosit_vyzov` | Сброс |
| `button.smartintercom_otkryt_seichas` | Открыть сейчас |
| `select.smartintercom_deistvie_po_umolchaniiu` | Режим |
| `script.empire_domofon_otkryt` | Скрипт для Алисы / дашборда |

Пакет: `homeassistant/packages/empire_domofon.yaml`.

## Автооткрытие

Сущность: `select.smartintercom_deistvie_po_umolchaniiu` (веб устройства / HA).

| Режим | Что делает |
|--------|------------|
| **Не активен** | Обычный режим: трубка + TG/Алиса, открытие вручную |
| **Открывать всегда** | Каждый звонок → автооткрытие (трубка обычно молчит) |
| **Сбрасывать вызов** | Каждый звонок → отказ |
| **Управление с трубки** | Линия на трубку без автологики модуля |

Разово (один следующий звонок):

| Switch | Смысл |
|--------|--------|
| `switch.smartintercom_otkryt_dver` | Открыть при следующем звонке |
| `switch.smartintercom_otkryt_kureru` | То же + MP3 курьеру |
| `switch.smartintercom_sbrosit_vyzov` | Сброс при следующем звонке |

В HA: Устройства → SmartIntercom → **Действие по умолчанию** → `Открывать всегда`.  
Или сервис: `select.select_option` → `Открывать всегда`.  
Вернуть норму: снова `Не активен`.

> Залипшее разовое «Открыть»/«Курьер» глушит трубку; автоматизации сбрасывают их через 15 мин. Постоянный режим — только через select, не через эти switch.

## Управление

| Канал | Действие |
|--------|----------|
| **Telegram** (@stepanich_ogorod_bot, Николай Степанович) | `/domofon` — меню режимов; при звонке: кнопки Открыть / Курьер / Сброс |
| **Алиса (колонки)** | Параллельно с TG: TTS «Звонок в домофон» на все `media_player` Yandex Station |
| HA дашборд | Коридор → Открыть |
| Алиса (голос) | «Открой домофон» → `script.empire_domofon_otkryt` |

Кнопки TG: `ha_telegram_bridge` клеит inline-клавиатуру на текст «Звонок в домофон!»; callback обрабатывает `empire_main` → HA MQTT.

### Алиса: что нужно один раз

Компонент `yandex_station` уже в HACS, но **интеграция не добавлена** (нет `media_player.*`).  
HA → Настройки → Устройства → Добавить → **Yandex Station** → вход по **QR**.  
После появления колонок автоматизация `empire_domofon_call_notify` озвучит все станции параллельно с TG. Трубка при этом звонит сама по линии.

## Почему не звонит штатная трубка

По wiki / ручной / TG `@smartintercom` и текущим настройкам BlueStreak:

1. **Залипли «Открыть дверь» или «Курьер»** — модуль сразу занимает линию (открытие / MP3 курьеру), трубка молчит. Должны быть **off**. Автоматизации сбрасывают залипание через 15 мин.
2. **«Рингтон» в веб-UI** — это MP3 на **цифровой COMMAX**, не звонок аналоговой трубки Laskomex. `ringtone: false` для аналога нормален.
3. **Аудиосообщения** (`sound`) — звук на **подъездный блок**, не в трубку.
4. **Монтаж в разрыв** (LN+/LN− линия, PH+/PH− трубка), полярность. Если PH не подключены или перепутаны — детектор в HA может сработать, а трубка нет.
5. В прошивке ESPHome (старый путь) отдельно есть **mute** / **phone_disable** — глушат трубку. В BlueStreak этих тумблеров в getSettings нет; аналог по симптомам — п.1.

Проверка: оба switch off → `line_detect`/`Детектор вызова` = on при звонке → трубка должна звенеть параллельно с TG/Алисой.

## Проверка

1. HA → Устройства → **SmartIntercom** — online.  
2. Позвоните в домофон → TG с кнопками + `binary_sensor.smartintercom_detektor_vyzova` = on.  
3. Нажмите **Открыть** в TG или Алиса «открой домофон».

Веб устройства: http://192.168.1.101/ (MQTT: сервер `192.168.1.41`, порт `1883`).

## ESPHome

Не требуется. Старый путь: `docs/HA_SMARTINTERCOM_ESPHOME.md` (legacy).
