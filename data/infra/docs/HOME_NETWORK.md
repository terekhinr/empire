# Домашняя сеть — Flint 2 (GL-MT6000)

## Текущая схема

- **Роутер:** только Flint 2, vanilla OpenWrt **24.10.4**
- **LAN:** `192.168.1.1/24` (как был Keenetic)
- **Wi‑Fi:** SSID **Destroy**, PSK — в `/root/.keenetic-admin.env` или наклейка / экспорт Keenetic
- **HA:** `192.168.1.41`, Tailscale `100.80.133.85`
- **Workgroup Samba:** **HOME** (как Keenetic)

## Маршрутизация трафика

Два режима (подробно: [`docs/FLINT2_YOUTUBE_DUAL.md`](../FLINT2_YOUTUBE_DUAL.md)):

| Режим | YouTube / блокировки РФ | Как включить |
|--------|-------------------------|--------------|
| **A — с VPS** (по умолчанию дома) | podkop → VLESS Empire `:8443` | `00-bootstrap.sh` / `20-mode-vps.sh` |
| **B — без VPS** | zapret (DPI), без туннеля | `00-bootstrap-novps.sh` / `21-mode-novps.sh` |

В режиме A:

| Трафик | Куда | Как проверить |
|--------|------|---------------|
| YouTube, Meta, TikTok… | VLESS → Empire `:8443` | `curl -I https://www.youtube.com/generate_204` с Flint |
| Telegram | VLESS + список `telegram` | web.telegram.org с ПК без Amnezia |
| OpenAI, Claude, Яндекс AI | **awg0** Amnezia (если туннель жив) | `awg show awg0` handshake |
| Остальное | WAN напрямую | — |

Обязательно: **vanilla OpenWrt**, flow offloading **выкл**, IPv6 WAN **выкл**. Zapret и podkop не должны резать один и тот же домен сразу.

**Amnezia на ПК дома — выключать** (конфликт с Flint).

## Доступ к Flint

| Способ | Команда / URL |
|--------|----------------|
| С LAN | `ssh root@192.168.1.1` · LuCI http://192.168.1.1 |
| **PWA автопочинка** | **http://192.168.1.1/empire/** (токен `/etc/empire/flint-ui.token` на VPS) |
| Зеркало PWA | https://neverretire.ru/home-ops/ |
| HA с улицы (Tailscale) | https://moderate-amethys.tailed4746.ts.net:10000/ |
| HA + LAN с телефона | Tailscale → Approve subnet `192.168.1.0/24` (`scripts/enable_ha_tailscale_subnet.sh`) → http://192.168.1.41:8123 |
| **Телефон без VPS (LTE)** | **Tailscale на Flint** — [PHONE_ACCESS_NO_VPS.md](PHONE_ACCESS_NO_VPS.md) |
| WireGuard phone | CGNAT (`100.83.x.x`): с мобильного **не работает** |
| Через HA SSH | `ssh root@100.80.133.85` → `ssh root@192.168.1.1` |
| С VPS (туннель) | `ssh -p 6223 root@127.0.0.1` |

**Автоматика:**

- На Flint каждые 5 мин: `empire-flint-watchdog` (локально, без ИИ).
- На VPS: `empire-service-healer`, `empire-router-watchdog`, morning-brief.

Подробности: [SELF_HEAL.md](SELF_HEAL.md), [empire-flint-watchdog/README.md](../../scripts/flint2/empire-flint-watchdog/README.md).

**Пароль root Flint:** `/root/.flint-admin.env` на VPS (не в git).

## USB / Transmission / Samba

| Что | Значение |
|-----|----------|
| Диск | NTFS UUID `01D63D133C7B6100` (устройство `sda6` или `sdb6` после реконекта) |
| Mount | `/mnt/usb` |
| Загрузки | `/mnt/usb/download` |
| Samba | `\\192.168.1.1\download` (Win+R, не ждать «Сеть») |
| Transmission | 24/7, RPC `http://192.168.1.1:9091` |
| Трекеры (rutracker и др.) | через VLESS, как YouTube (`18-torrent-sites.sh`) |
| fstab | `UUID=01D63D133C7B6100 /mnt/usb ntfs-3g defaults,nofail 0 0` |

## Скрипты на VPS (bootstrap)

Сервер: `http://193.233.232.48:8789/` → каталог `scripts/flint2/`

| Скрипт | Назначение |
|--------|------------|
| `00-bootstrap.sh` | Полная первичная настройка |
| `03-config-podkop.sh` | VLESS + telegram + ai_awg |
| `09-amnezia-awg-split.sh` | Amnezia + dnsmasq-full |
| `12-usb-samba-transmission.sh` | USB + Samba + Transmission |
| `14-podkop-ai-telegram.sh` | Фикс AI/TG |
| `15-samba-home.sh` | workgroup HOME |
| `16-fix-gemini.sh` | Gemini → VLESS |

## Бэкап конфигурации Flint

**Автоматически** (с VPS, если HA доступен):

```bash
sudo bash /root/projects/empire/scripts/infra/home_router_backup.sh
```

**Вручную на Flint:**

```bash
uci export > /tmp/flint-uci-backup.conf
tar czf /tmp/flint-etc-config.tar.gz /etc/config/
# скопировать на ПК или на VPS
```

Файлы попадают в `data/infra/home-router/` и на Я.Диск в `infra/`.

## Восстановление Flint с нуля

1. Прошить [OpenWrt 24.10.4 sysupgrade](https://firmware-selector.openwrt.org/?version=24.10.4&target=mediatek%2Ffilogic&id=glinet_gl-mt6000) **без** сохранения настроек.
2. Подключить кабель LAN, зайти `192.168.1.1`.
3. Вариант A — bootstrap: `curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh`
4. Вариант B — восстановить UCI из бэкапа:
   ```bash
   scp flint-uci-backup.conf root@192.168.1.1:/tmp/
   ssh root@192.168.1.1 "uci import < /tmp/flint-uci-backup.conf && /etc/init.d/network restart"
   ```
5. Положить `/etc/amnezia/client.env` из бэкапа или заново из Amnezia `.vpn`.
6. Вставить USB, запустить `12-usb-samba-transmission.sh`.
7. Чеклист: DNS, YouTube, Telegram, Samba, awg handshake.

## Известные проблемы

| Симптом | Причина | Действие |
|---------|---------|----------|
| Нет DNS на всех устройствах | `ai-vpn.nftset` без dnsmasq-full | `opkg install dnsmasq-full`, убрать nftset или поставить full |
| Gemini не грузится / крутится | только `google_ai` (без accounts/gstatic) или нет reload | `16-fix-gemini.sh` + Ctrl+F5; DNS должен быть FakeIP `198.18.*` |
| Диск Z: не найден | Старый `\\Keenetic\download` | `\\192.168.1.1\download` |
| podkop «not running» | sing-box жив, сервис отвалился | `/etc/init.d/podkop restart` |

Подробнее: `docs/FLINT2_SETUP.md`, `docs/FLINT2_FIX_HOME_AI_TG.md`.
