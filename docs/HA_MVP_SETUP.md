# Home Assistant MVP — шаги после дашборда

Инстанс: `http://192.168.1.41:8123` (Tailscale: `100.80.133.85`).

## Сделано

- [x] 10 зон (areas)
- [x] Режимы `input_boolean` + группа
- [x] Дашборд Empire
- [x] ZHA: координатор **Sonoff Zigbee 3.0 USB Dongle Plus V2** (устройств Zigbee пока 0)

## Шаг 1. Telegram в HA ✅

Цепочка: HA → `http://172.30.32.1:8766/notify` (прокси на armbian) → VPS мост (`8877`) → Telegram.

- `secrets.yaml`: `ha_notify_url`, `ha_notify_token` (см. `secrets.yaml.example`)
- armbian: `systemctl status empire-ha-proxy` (active)
- VPS: `systemctl status empire_ha_notify` (порт **8877**)
- После **Tailscale на armbian** можно в прокси сменить URL на `http://100.84.19.35:8877/notify` (вместо публичного IP)

Проверка: сценарий **«Empire — тест Telegram»**.

## Шаг 2. ZHA — пейринг Zigbee

1. **Настройки → Устройства и службы → ZHA** → **Добавить устройство**.
2. Приоритет по ТЗ: датчик движения (прихожая/коридор), протечка (кухня/ванная), temp/hum.
3. Каждое устройство: **Настройки → Область** — назначить комнату.

Координатор уже в сети; `zigbee.db` в `/config` — не удалять.

## Шаг 3. Tuya Cloud → LocalTuya

Сейчас интеграция **Tuya (облако)** в состоянии `setup_error` — для политики «только локально»:

1. **Настройки → Устройства → Tuya** — исправить или **удалить** облачную интеграцию.
2. Установить **HACS → LocalTuya** (если ещё нет) в `custom_components`.
3. Для каждой лампы/розетки Tuya:
   - Узнать **local_key** (Tuya IoT / tinytuya / tuya-cli).
   - LocalTuya → Add device → IP в LAN, `device_id`, `local_key`, версия 3.3/3.4.
4. Назначить area; проверить управление при **отключённом интернете**.

Розетки (бойлер/техника): привязать к area **Кухня** или отдельная зона; в отпуске — авто OFF (автоматизация позже).

## Шаг 4. Облачная Tuya

Не использовать для автоматизаций. LocalTuya only.

## Шаг 5. Домофон

BlueStreak: `http://192.168.1.65/` — DHCP reservation на роутере. ESPHome — **фаза 4** (после основного HA).

## Шаг 6. Резерв

Установить add-on **Home Assistant Google Drive Backup** → расписание раз в неделю.

## Шаг 7. Следующая фаза (по ТЗ)

- Ezviz (2+ камеры), Dreame, Haier IR, Yandex Smart Home, empire-бот ↔ HA.
