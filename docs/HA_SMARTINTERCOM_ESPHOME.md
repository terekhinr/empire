# SmartIntercom → ESPHome + Home Assistant

Устройство: [SCratORS/SmartIntercom](https://github.com/SCratORS/SmartIntercom) · IP **`192.168.1.65`** · блок **Laskomex LM-8D**.

## Что уже в репозитории

| Путь | Назначение |
|------|------------|
| `homeassistant/esphome/smartintercom-esp32.yaml` | Прошивка ESPHome |
| `homeassistant/esphome/partitions_esp32.csv` | Таблица разделов ESP32 |
| `homeassistant/esphome/lib/` | ESPAudio.h, ESPUtils.h |
| `homeassistant/esphome/data/*.mp3` | Аудио для FTP после прошивки |
| `homeassistant/packages/empire_domofon.yaml` | Telegram + скрипт «Открыть» |
| `deploy/ha_deploy_smartintercom.sh` | Деплой на HA |

## 1. Деплой конфигов на HA

```bash
cd /root/projects/empire
bash deploy/ha_deploy_smartintercom.sh
```

Скрипт копирует ESPHome-проект в `/config/esphome/`, генерирует `esphome_api_key` / `esphome_ota_password` в `secrets.yaml`, обновляет дашборд и автоматизации.

## 2. Переход с BlueStreak на ESPHome

### Вариант A — OTA из BlueStreak (рекомендуется)

1. Откройте **`http://192.168.1.65/`** (BlueStreak).
2. **Дополнительно → Обновление прошивки**.
3. Загрузите файл  
   [`bin/esphome_1.7.6.esp32ota.bin`](https://github.com/SCratORS/SmartIntercom/raw/main/bin/esphome_1.7.6.esp32ota.bin).
4. Дождитесь перезагрузки (устройство подключится к Wi‑Fi из `secrets.yaml`).

### Вариант B — USB (голый ESP / аварийная прошивка)

Через ESP Download Tool, см. [README](https://github.com/SCratORS/SmartIntercom#если-ничего-не-прошито-голая-прошивка--аварийная-перепрошивка):

- `ESP32_smartintercom.bin` @ `0x0`
- `ESP32_mklittlefs_0x2B0000.bin` @ `0x2B0000`

## 3. Компиляция и установка из HA

1. **Настройки → Дополнения → ESPHome** (уже установлен).
2. Откройте addon → **smartintercom** (появится после деплоя).
3. **Install → Wirelessly** (если уже на ESPHome) или **Plug into this computer** (USB‑TTL).

> В README автор рекомендует ESPHome Builder **< 2025.2.0**. В конфиге уже есть `external_components` для совместимости с новыми версиями. Если сборка падает — напишите в лог ошибку.

## 4. Загрузка MP3 (обязательно после первой прошивки)

1. Устройство **ONLINE** в ESPHome.
2. FTP к **`192.168.1.65`**: passive, **anonymous**, без TLS.
3. Скопируйте `*.mp3` из `/config/esphome/data/` на HA **в корень FTP** устройства:
   - `user_greeting.mp3`
   - `user_access_allowed.mp3`
   - `delivery_access_allowed.mp3`
   - `access_denied.mp3`

## 5. Сущности в HA

| Entity | Описание |
|--------|----------|
| `binary_sensor.smartintercom_line_detect` | Идёт вызов |
| `sensor.smartintercom_line_status` | Вызов / Ответ / Открытие / Сброс / Закрыто |
| `select.smartintercom_modes` | Не активен / Сброс вызова / Открывать всегда |
| `switch.smartintercom_accept_call` | Открыть |
| `switch.smartintercom_delivery` | Курьер |
| `switch.smartintercom_reject_call` | Сброс |
| `switch.smartintercom_mute` | Без звука на блоке |
| `switch.smartintercom_phone_disable` | Линия на модуле (трубка отключена) |
| `sensor.smartintercom_ip` | IP в LAN |

## 6. Автоматизации Empire

- **Telegram:** `binary_sensor.smartintercom_line_detect` → «Звонок в домофон!»
- **Алиса:** «Открыть домофон» → `script.empire_domofon_otkryt`
- **Дашборд:** вкладка **Коридор** — кнопки Открыть / Курьер / Сброс

## 7. Роутер

Закрепите DHCP по MAC модуля → **`192.168.1.65`**.

## 8. Проверка

1. Позвоните в домофон → Telegram + карточка «Вызов» на дашборде.
2. **Открыть** → дверь открывается, статус «Открытие двери».
3. Алиса: «Открой домофон».

Обсуждение: [Telegram канал SmartIntercom](https://t.me/smartintercom).
