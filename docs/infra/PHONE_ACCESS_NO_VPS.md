# Доступ к роутеру с телефона без VPS

## Почему WireGuard с LTE не работает

У провайдера **CGNAT**: WAN Flint = `100.83.x.x` (не белый IP).  
С мобильного интернета до `WAN:51820` пакеты **не доходят**. Это не баг Flint.

## Рабочий способ: Tailscale (без твоего VPS)

Tailscale сам пробивает NAT (DERP). VPS Empire **не нужен**.

### 1. Роутер Flint в Tailscale

На Flint установлен пакет `tailscale`. После перезагрузки/перелогина:

```sh
tailscale up --advertise-routes=192.168.1.0/24 --accept-routes --hostname=flint2
```

Открой ссылку `https://login.tailscale.com/a/...` в браузере (тот же аккаунт, что на телефоне).

### 2. Approve subnet в админке

1. https://login.tailscale.com/admin/machines  
2. Машина **flint2** (и/или **armbian**) → **Edit route settings**  
3. Approve **`192.168.1.0/24`**

Без Approve с телефона виден только сам узел Tailscale, не весь LAN.

### 3. Телефон

1. Приложение **Tailscale** → Connected (тот же аккаунт).  
2. В настройках телефона: **Use Tailscale subnets / Accept routes** = ON.  
3. Открой:

| Что | URL |
|-----|-----|
| Роутер LuCI / PWA | `http://192.168.1.1/` · `http://192.168.1.1/empire/` |
| HA | `http://192.168.1.41:8123` |
| Transmission | `http://192.168.1.1:9091/transmission/web/` |
| Samba (если клиент умеет) | `\\192.168.1.1\download` или SMB-клиент |

Либо по Tailscale-IP Flint (`tailscale status` → адрес `100.x` у `flint2`).

### 4. HA Companion

- Внутренний: `http://192.168.1.41:8123`  
- Внешний: тот же `http://192.168.1.41:8123` (когда Tailscale Connected + subnet approved)

HTTPS через VPS `:10000` — опционально, для Companion без subnet; для «без VPS» не нужен.

## Обновление Tailscale на Flint

В OpenWrt 24.10 из opkg только **1.80.3**. Рабочая версия ставится с официального CDN (`arm64`).

**Важно:** на OpenWrt `/var → /tmp` (RAM). Без `--statedir=/etc/tailscale/statedir` логин «успешен» в админке, но через минуту машина **Offline** (ключ в tmpfs). Init: `scripts/flint2/empire-flint-watchdog/tailscale.init`.

**CGNAT WAN:** у провайдера адрес `100.83.x.x` лежит в диапазоне Tailscale `100.64.0.0/10`. Режим netfilter по умолчанию **режет интернет через роутер**. Обязательно:

```sh
tailscale set --netfilter-mode=off
```

```sh
# бинарники 1.98.x + persistent state
/etc/init.d/tailscale stop
# ... copy tailscale/tailscaled from pkgs.tailscale.com arm64 tgz ...
mkdir -p /etc/tailscale/statedir
# init должен запускать: tailscaled --statedir /etc/tailscale/statedir --state .../tailscaled.state
/etc/init.d/tailscale start
tailscale up --hostname=flint2 --advertise-routes=192.168.1.0/24 --accept-routes --accept-dns=false
```

После логина: https://login.tailscale.com/admin/machines → Approve `192.168.1.0/24` для **flint2**. Старые offline `flint2` / `flint2-1` можно удалить.

