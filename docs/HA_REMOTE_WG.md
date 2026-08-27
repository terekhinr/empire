# Удалённый доступ к HA (Companion)

## Основной способ: WireGuard

Конфиг на домашнем диске:

`\\192.168.1.1\download\WireGuard\phone.conf`

(рядом `README.txt`)

1. Телефон → приложение **WireGuard** → импорт `phone.conf`.
2. Включать **только вне дома**.
3. **Home Assistant Companion:**
   - Внутренний URL: `http://192.168.1.41:8123`
   - Внешний URL: `http://192.168.1.41:8123`
4. Также: роутер `http://192.168.1.1`, Transmission `http://192.168.1.1:9091`.

Endpoint: белый IP провайдера `:51820` (если сменится — обновить в `phone.conf`).

## Tailscale

Для HA с LTE Tailscale HTTPS Serve сейчас **не работает** (Armbian не получает сертификат ACME).  
HTTP `http://100.80.133.85:8123` по Tailscale жив, но Companion часто требует HTTPS.

Итого для Companion: **WireGuard**, не Tailscale.
