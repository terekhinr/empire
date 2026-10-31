# Самопочинка Empire (без ИИ)

## Полная картина

Слои, варианты и практика HA-мониторинга: [`docs/HEALER_ARCHITECTURE.md`](../HEALER_ARCHITECTURE.md).

## HA device healer (на Flint)

Каждые 5 мин на роутере: `/usr/sbin/empire-ha-healer`  
Залипание occupancy (ванна/туалет), свет без присутствия, unavailable ZHA/LocalTuya, ping SmartIntercom, restart HA API.

Код: `scripts/flint2/empire-ha-healer/` · лог `/tmp/empire-ha-healer.log`  
Установка: `bash scripts/flint2/empire-ha-healer/install.sh`

**UI:** блок «HA хилер» в PWA — [http://192.168.1.1/empire/](http://192.168.1.1/empire/) и зеркало [https://neverretire.ru/home-ops/](https://neverretire.ru/home-ops/) (кнопки «Прогнать» / «Принудительно»).

## HA watcher (на VPS)

`scripts/empire_ha_watcher.py` — API + critical entities + триггер Flint healer + опц. Healthchecks.  
Встроен в `empire-service-healer` (каждые ~5 мин). Ручной прогон: `./venv/bin/python scripts/empire_ha_watcher.py --check`.

## PWA на роутере (главное)

Открой с домашнего Wi‑Fi (или через Tailscale после Approve subnet):

**http://192.168.1.1/empire/**

Токен лежит на VPS: `/etc/empire/flint-ui.token`  
Первый заход: `http://192.168.1.1/empire/?token=…` — сохранится в телефоне.

Кнопки: «Починить всё», podkop/YouTube, Zapret, Amnezia, туннель VPS, перезапуск HA.

Сторож CLI: каждые 5 мин `/usr/sbin/empire-flint-watchdog` на Flint.  
USB/Samba: каждую минуту remount NTFS по UUID + smbd; шара `\\192.168.1.1\download` (логин `home`/`home`).  
Режимы YouTube (VPS / zapret без VPS): [`docs/FLINT2_YOUTUBE_DUAL.md`](../FLINT2_YOUTUBE_DUAL.md).

## Зеркало с VPS

**https://neverretire.ru/home-ops/** (тот же токен)  
Прокси → reverse SSH → Flint API. Нужен живой туннель `:6223`.

Туннель на Flint: `/etc/flint2-tunnel/start.sh` (канон в репо: `scripts/flint2/flint2-tunnel-start.sh`).  
`VPS` должен совпадать с **текущим** Empire-хостом. Reverse (`-R :6223`) обязателен; VLESS `-L :18443` — optional.

## Доступ к HA с улицы

1. Уже работает зеркало: `https://moderate-amethys.tailed4746.ts.net:10000/` (Tailscale).
2. Subnet LAN: `bash scripts/enable_ha_tailscale_subnet.sh` → в админке Tailscale **Approve** `192.168.1.0/24`.
3. На телефоне Tailscale Online → `http://192.168.1.41:8123` и `http://192.168.1.1/empire/`.

## WireGuard

Конфиг телефона: `/etc/empire/flint-wg-phone.conf`  
Экспорт: `bash scripts/flint2/empire-flint-watchdog/export-wg-phone.sh`  

**CGNAT:** Endpoint = WAN Flint (`100.x`) с мобильного интернета **не достучится**. WG полезен в редких сетях без CGNAT / для тестов. Для улицы — Tailscale.

## Установка / обновление

```bash
bash scripts/flint2/empire-flint-watchdog/install.sh
```

Логи сторожа на Flint: `/tmp/empire-flint-watchdog.log`
