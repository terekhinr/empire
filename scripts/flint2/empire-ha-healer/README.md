# Empire HA Healer (на Flint)

Автохилер Home Assistant **на роутере** Flint 2. VPS не обязателен.

## Поведение (каждые 5 мин)

| Проверка | Действие |
|----------|----------|
| HA API мёртв | `homeassistant.restart` (cooldown 1 ч) |
| Zigbee light/sensor `unavailable` | reload ZHA (cooldown 1 ч) |
| Балкон SRW / LocalTuya `unavailable` | reload LocalTuya + TG про local_key |
| Occupancy **on > 45 мин** и свет горит | `light.turn_off` + TG (ванна / туалет) |
| Свет on при presence **off > 3 мин** | `light.turn_off` (+ raw HOBEIAN / TS0052) |
| SmartIntercom не пингуется (.101/.65) | TG |
| Нет `switch.smartintercom_accept_call` в HA | TG |

**Не трогает:** чувствительность Sonoff, failsafe-автоматики, принудительный `states.set` датчика.

## UI

| Где | URL |
|-----|-----|
| Дома (Flint) | http://192.168.1.1/empire/ |
| Снаружи | https://neverretire.ru/home-ops/ |

Блок **HA хилер**: присутствие/свет ванна+туалет, залипание, issues, домофон IP, лог, кнопки «Прогнать» / «Принудительно».

## Установка

С VPS:

```bash
bash scripts/flint2/empire-ha-healer/install.sh
```

На Flint:

```sh
sh install-local.sh
```

Нужны в `/etc/empire-flint-ui.env`: `HA_URL=http://192.168.1.41:8123`, `HA_TOKEN=…`

## Команды

```sh
/usr/sbin/empire-ha-healer --check   # только отчёт
/usr/sbin/empire-ha-healer --force   # игнор cooldown
EMPIRE_HA_HEAL_VERBOSE=1 empire-ha-healer
```

Лог: `/tmp/empire-ha-healer.log` · State: `/tmp/empire-ha-healer.state`  
Пороги: `/etc/empire-ha-healer.env`
