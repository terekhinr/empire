# Flint 2 — как зайти в админку БЕЗ Cursor / ИИ

Роутер: **OpenWrt**, не Keenetic. Админка другая.

## Адрес (только из домашней сети)

| Что | URL |
|-----|-----|
| Админка LuCI | **http://192.168.1.1/** |
| Если просит HTTPS | **http://192.168.1.1/** (не https) или прими самоподписанный сертификат на :443 |
| Empire PWA | http://192.168.1.1/empire/ |
| Transmission | http://192.168.1.1:9091/transmission/web/ |
| Samba | `\\192.168.1.1\download` |

**Wi‑Fi:** SSID **Destroy** (как раньше).

## Если «не открывается»

1. Телефон/ПК должны быть в Wi‑Fi **Destroy** или кабелем в LAN.  
   На **мобильном интернете** `192.168.1.1` **не существует** — это только домашний адрес.
2. Выключи VPN на устройстве: **Amnezia / Tailscale / WireGuard** на время входа в админку.
3. На ПК: `Win+R` → `cmd` →  
   `ping 192.168.1.1`  
   `ipconfig` — шлюз должен быть `192.168.1.1`.
4. Браузер: попробуй **другой** (Chrome / Edge) или режим инкогнито.  
   Не `http://keenetic` / не старый IP.
5. Жёсткий сброс сети на телефоне: забыть Wi‑Fi Destroy → подключить снова.

## Логин LuCI

- Пользователь: **root**
- Пароль: тот, что задавали при настройке Flint (файл на VPS: `/root/.flint-admin.env`, не в git).  
  Если забыли — сброс кнопкой Reset на корпусе (потеряет настройки).

## Оживить интернет «как Keenetic» без ИИ

По SSH с ПК в LAN (`ssh root@192.168.1.1`):

```sh
/etc/init.d/podkop restart
/etc/init.d/zapret2 restart
/etc/init.d/network restart   # осторожно — на секунды пропадёт Wi‑Fi
```

Только YouTube/прокси:

```sh
/usr/sbin/empire-flint-watchdog --force
```

Только диск/шара:

```sh
/etc/init.d/empire-usb-mount start
/etc/init.d/samba4 restart
```

Tailscale (если снова убил интернет — у нас CGNAT `100.83.x`):

```sh
tailscale set --netfilter-mode=off
```

## Failsafe (если совсем кирпич)

1. Зажать Reset ~10 сек → OpenWrt failsafe / сброс.  
2. Кабель в LAN, ПК: IP `192.168.1.2`, шлюз `192.168.1.1`.  
3. Открыть `http://192.168.1.1/` и настроить заново или bootstrap:  
   `curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh`

Подробнее: `docs/infra/HOME_NETWORK.md`, `docs/infra/PHONE_ACCESS_NO_VPS.md`.
