# Empire: автономный watchdog устройств (без Cursor)

**Канон стабильности (HAOS vs Supervised, протоколы, слои):** `docs/HA_STABILITY_ARCHITECTURE.md`

## Слои (кто что делает)

| Слой | Где | Расписание | Что |
|------|-----|------------|-----|
| **HA `empire_device_watchdog`** | Home Assistant packages | события + каждые 6ч скан | TG: какой датчик/свет offline, залип presence; soft reload ZHA/LocalTuya (1/ч) |
| **Flint `empire-ha-healer`** | Роутер OpenWrt | cron `*/5` | LAN: unavailable → reload; stuck occupancy → light off; HA API down → restart 1/ч; TG |
| **VPS `empire_ha_watcher`** | `empire-service-healer.timer` 5 мин | дайджест отвалов в TG + триггер Flint `--force` |

Cursor / IDE **не участвует**. После деплоя всё крутится само.

## Безопасность

- Cooldown reload ZHA/LocalTuya: **1 час**
- HA core restart: только с Flint при мёртвом API, **1/час**, флаг `ALLOW_HA_RESTART`
- Bathroom light: VPS watcher **не гасит** при offline presence (только отчёт)
- Desync light-off на Flint: presence=off + light=on ≥ **5 мин**
- TG cooldown на одинаковый ключ: **30 мин** (Flint)

## Деплой

```bash
# HA package
scp homeassistant/packages/empire_device_watchdog.yaml root@100.80.133.85:/usr/share/hassio/homeassistant/packages/
# UI: reload Automations + Scripts + input_datetime (или restart HA)

# Flint healer (с VPS)
bash scripts/flint2/empire-ha-healer/install.sh
# или вручную на Flint:
# curl -fsSL http://<VPS>:8789/empire-ha-healer/empire-ha-healer -o /usr/sbin/empire-ha-healer
```

## Ручная проверка

```bash
# VPS
./venv/bin/python scripts/empire_ha_watcher.py --check

# Flint
ssh -p 6223 root@127.0.0.1 '/usr/sbin/empire-ha-healer --check'
```
