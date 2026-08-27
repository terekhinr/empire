# Самопочинка Empire (без ИИ)

## PWA на роутере (главное)

Открой с домашнего Wi‑Fi (или через Tailscale после Approve subnet):

**http://192.168.1.1/empire/**

Токен лежит на VPS: `/etc/empire/flint-ui.token`  
Первый заход: `http://192.168.1.1/empire/?token=…` — сохранится в телефоне.

Кнопки: «Починить всё», podkop/YouTube, Zapret, Amnezia, туннель VPS, перезапуск HA.

Сторож CLI: каждые 5 мин `/usr/sbin/empire-flint-watchdog` на Flint.

## Зеркало с VPS

**https://neverretire.ru/home-ops/** (тот же токен)  
Прокси → reverse SSH → Flint API. Нужен живой туннель `:6223`.

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
