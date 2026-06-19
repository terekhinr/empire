# Дополнения Home Assistant (Supervised) — рекомендации empire

**Проверено по API:** май 2026, `100.80.133.85`.

## Уже есть (по проекту)

| Дополнение | Зачем |
|------------|--------|
| **HACS** | LocalTuya, SonoffLAN, Yandex Smart Home |
| **File editor** | packages, secrets |
| **SSH** | armbian / config |
| **Tailscale** | удалённый доступ |
| **ESPHome** | домофон (фаза 4) |

## Zigbee: выбрано **ZHA** (не Zigbee2MQTT)

| | ZHA ✅ | Zigbee2MQTT ❌ |
|---|--------|----------------|
| Статус | **loaded**, координатор Sonoff Plus V2 | не ставить |
| USB | уже у ZHA | конфликт с ZHA |
| MQTT | не нужен | нужен Mosquitto |
| ТЗ empire | да | миграция + перепривязка |

**Не устанавливать:** дополнение **Zigbee2MQTT**, **Mosquitto** (только ради Zigbee).

## Рекомендуется добавить

| Дополнение | Приоритет |
|------------|-----------|
| **Google Drive Backup** | высокий — бэкап `/config` |
| **Mosquitto** | только если появятся **не-Zigbee** MQTT-устройства |
| **Studio Code Server** | опционально (удобнее File editor) |
| **Samba share** | опционально — копирование с ПК |
| **Terminal** | если ещё нет в UI |

## Не нужны сейчас

- **Zigbee2MQTT** — дублирует ZHA  
- **Node-RED** — пока automations в yaml достаточно  
- **Frigate** — камеры Ezviz позже, другой путь  

## Интеграции (не дополнения)

| Интеграция | Статус | Действие |
|------------|--------|----------|
| **ZHA** | loaded | пейринг устройств |
| **Tuya Cloud** | setup_error | **удалить** → LocalTuya |
| **HACS** | loaded | LocalTuya, SonoffLAN |
| **Bluetooth** | setup_retry | можно игнорировать, если BLE не используете |

## ZHA — заметки по API

Обнаружены сущности `unavailable` (частичный пейринг):

- `switch.on_off_switch_switch_1`, `switch.w602_switch_1` …

**Действие:** ZHA → устройство → удалить «мёртвые» → **Добавить устройство** заново (permit join).

Включён **permit join 60 с** с VPS (разово) — при необходимости в UI: ZHA → «Разрешить подключение».
