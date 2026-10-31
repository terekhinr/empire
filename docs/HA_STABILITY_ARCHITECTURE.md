# Стабильность Home Assistant — канон Empire (2026-10)

**Цель:** HA и автоматика не «умирают»; Zigbee / MQTT / LocalTuya / домофон доступны без ручного Cursor.

**Не трогать:** маршруты Flint (ИИ / YouTube / TG) — см. `.cursor/rules/flint-vpn-freeze.mdc`.

---

## Как у других (консенсус сообщества 2025–2026)

| Вариант | Суть | Вердикт для нас |
|---------|------|-----------------|
| **HAOS** (официальный appliance) | OS + Supervisor + watchdog аддонов | **Цель на горизонте** — Supervised официально deprecated |
| **Supervised на Debian/Armbian** | Как сейчас | Работает, но `supported: false` — без гарантий апдейтов |
| **Container (compose) без Supervisor** | Гибко, без add-ons store | Хуже для Mosquitto/бэкапов «из коробки» |
| **Zigbee2MQTT + Mosquitto** | Отдельный процесс + MQTT | Не мигрируем: уже **ZHA**, второй стек = конфликт USB |
| **3 слоя watchdog** (внешний / canary внутри HA / рестарт аддонов) | Big Iron / community | **Делаем сейчас** — у нас уже набросок |

Источники: [HA blog: deprecating Supervised](https://www.home-assistant.io/blog/2025/05/22/deprecating-core-and-supervised-installation-methods-and-32-bit-systems/), community watchdog stack (external heartbeat + canaries + addon watchdog).

---

## Выбранная схема (два горизонта)

### Горизонт A — сейчас (без смены железа)

Оставить **Supervised на Armbian**, не ломая ZHA / MQTT / LocalTuya, усилить самолечение.

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1 — ВНЕ HA (VPS)                                  │
│  empire-service-healer + empire_ha_watcher (каждые 5м)  │
│  дайджест 07/20 MSK · /ha по запросу                    │
│  алерт/хил НЕ только через автоматики HA                │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│ Layer 2 — внутри HA                                     │
│  packages: motion lights, domofon, quiet device watchdog│
│  soft reload ZHA/LocalTuya (cooldown 1ч)                │
│  без realtime TG-спама                                  │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│ Layer 3 — Supervisor / хост                             │
│  core watchdog: ON                                      │
│  addon watchdog: Mosquitto, Tailscale, SSH, ESPHome ON  │
│  Google Drive Backup (уже есть)                         │
│  Flint empire-ha-healer (LAN/API, без правок VPN)       │
└─────────────────────────────────────────────────────────┘
```

**Протоколы (не смешивать):**

| Протокол | Стек | Не делать |
|----------|------|-----------|
| Zigbee | **ZHA** (Sonoff stick) | Не ставить Zigbee2MQTT на тот же USB |
| MQTT | **Mosquitto** только SmartIntercom | Не тащить весь Zigbee в MQTT |
| Wi‑Fi Tuya | **LocalTuya** | Не дублировать cloud Tuya без нужды |
| Камеры | Ezviz / generic | Отдельно от Zigbee |

### Горизонт B — когда будет окно (1 вечер + бэкап)

Миграция **Supervised → HAOS** на том же или новом x86/ARM боксе (официальный путь).  
Перенос: полный backup Supervisor → restore на HAOS. USB Zigbee сохранить.  
Это убирает `supported: false` и даёт нормальные апдейты.

**Не делать сейчас:** смена ZHA→Z2M, полный docker-compose rewrite, трогать Flint VPN.

---

## Что уже включено (2026-10-22)

- HA Core **watchdog: true**
- Addon **watchdog: true** — Mosquitto, Tailscale (+ SSH/ESPHome уже были)
- VPS healer + HA watcher + quiet digest / `/ha`
- Google Drive Backup addon

## Железо vs софт

Автоматика «умирает» часто не из‑за YAML, а потому что:

1. **Координатор / устройство Zigbee offline** (прихожая Zbeacon, HOBEIAN timeout) — питание, mesh, USB stick.
2. **SRW/Tuya sleep** — кнопка на датчике / Wi‑Fi.
3. **Mosquitto упал** после рестарта HA — теперь watchdog должен поднимать сам.
4. **Диск/RAM** на Armbian (следить: `/` не >85%, RAM available >500M).

---

## Чеклист владельца (раз в месяц)

1. HA → Настройки → Система → **Бэкапы** — свежий снимок + Google Drive.
2. Проверить аддоны: Mosquitto / Tailscale — **Watchdog** включён.
3. `./venv/bin/python tools/ha_health_check.py` с VPS.
4. Физика: офлайн Zbeacon прихожей, кнопка SRW балкона.

## Чеклист агента

- Не рестартить HA core без нужды (ломает MQTT discovery на минуты).
- Не ставить Z2M рядом с ZHA.
- Не менять Flint podkop/awg «ради HA».
- Хилить: soft reload entry → Mosquitto restart → только потом core restart.
