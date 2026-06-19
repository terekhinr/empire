# Фаза 2: ZHA + LocalTuya

После MVP (areas, режимы, Telegram). Инстанс: `192.168.1.41` / Tailscale `100.80.133.85`.

## Опционально: Tailscale на armbian

Если прокси сейчас ходит на публичный IP VPS:

```bash
# на armbian
tailscale status   # должен быть online, peer 100.84.19.35

sudo sed -i 's|VPS_NOTIFY_URL=.*|VPS_NOTIFY_URL=http://100.84.19.35:8877/notify|' \
  /etc/systemd/system/empire-ha-proxy.service
# или в Environment= в unit-файле
sudo systemctl daemon-reload && sudo systemctl restart empire-ha-proxy
```

Проверка: `curl -G "http://100.84.19.35:8877/notify" --data-urlencode "message=test tailscale" -H "Authorization: Bearer ВАШ_ТОКЕН"`

---

## 1. ZHA — первые устройства

**Координатор:** Sonoff Zigbee 3.0 USB Dongle Plus V2 (уже в HA).

1. **Настройки → Устройства и службы → ZHA → Добавить устройство**.
2. Режим пейринга на датчике (удержание кнопки — по инструкции производителя).
3. После добавления: **Настройки устройства → Область** — назначить комнату.

| Приоритет | Тип | Куда (по ТЗ) |
|-----------|-----|----------------|
| 1 | Движение | Прихожая, коридор |
| 2 | Протечка | Кухня, ванная |
| 3 | Температура/влажность | Спальня, детские |

**Не удалять** `/config/zigbee.db` при бэкапе — это база сети Zigbee.

### Автоматизация (после первого датчика движения)

Пример: ночной свет в коридоре — добавить в `empire_automations.yaml` когда появится `binary_sensor.*`.

---

## 2. Убрать Tuya Cloud

1. **Настройки → Устройства и службы → Tuya** → **Удалить** (сейчас `setup_error`).
2. Перезагрузка HA — в журнале не должно быть ошибок Tuya.

---

## 3. LocalTuya

1. **HACS** → Integrations → **LocalTuya** (если нет — установить).
2. Для каждой лампы/розетки Wi‑Fi Tuya в LAN:
   - IP в роутере (DHCP reservation).
   - `device_id`, `local_key` (tinytuya / Tuya IoT Developer — разовый облачный доступ для ключей).
   - Версия протокола 3.3 или 3.4.
3. **LocalTuya → Add device** → указать параметры.
4. **Область** — комната; проверить выключение при **отключённом интернете** (только LAN).

### Розетки (бойлер / техника)

- Area: Кухня или отдельная зона.
- Позже: автоматизация «Режим отпуск» → `switch.turn_off` на группу розеток.

---

## 4. Домофон (без изменений)

BlueStreak: `http://192.168.1.65/` — закрепить IP в роутере. ESPHome — **фаза 4**.

---

## 5. Резерв

Add-on **Home Assistant Google Drive Backup** → расписание 1× в неделю.

---

## 6. Чеклист готовности фазы 2

- [ ] 1+ Zigbee-устройство в ZHA с назначенной area
- [ ] Tuya Cloud удалён
- [ ] 1+ устройство LocalTuya (или список «жду ключи» в заметке)
- [ ] Lovelace: карточки устройств в комнатах (импорт `empire_main.yaml` при необходимости)
- [ ] Google Drive backup включён

Следующая фаза по ТЗ: Ezviz, Dreame, Haier IR, Yandex Smart Home.
