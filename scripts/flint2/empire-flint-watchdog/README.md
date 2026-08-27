# Empire Flint Watchdog + PWA

Автопочинка на Flint: раз в минуту `empire-lan-watch`, раз в 5 мин полный `empire-flint-watchdog`.

## Что само чинится
- sing-box / redirect `:1602`
- маршруты **Telegram + YouTube + торрент-трекеры** через VLESS (не затираются «slim»-фиксами)
- CIDR Telegram DC в nft
- zapret, DNS, USB, reverse SSH
- **Amnezia awg0**: свежий handshake (≤180s) + HTTP probe через `awg0` (не только «интерфейс есть»)
- снимок `/etc/podkop/sing-box.golden.json` — откат, если конфиг снова сломают

На VPS зеркало: `empire_router_watchdog` + `empire_service_healer` (peer `10.8.1.13` на `amnezia-awg2`).

## UI
Открой **https://neverretire.ru/home-ops/?token=…** (или дома `http://192.168.1.1/empire/?token=…`)  
Токен: `/etc/empire/flint-ui.token` на VPS.

## Установка
```bash
bash scripts/flint2/empire-flint-watchdog/install.sh
```
