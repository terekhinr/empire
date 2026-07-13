# Flint 2 (GL-MT6000) — настройка и миграция с Keenetic

Роутер: **GL.iNet GL-MT6000 (Flint 2)**  
Прошивка: **vanilla OpenWrt 24.10.4** (sysupgrade)  
Bootstrap VPS: `http://193.233.232.48:8789/`

## Что делает автоматизация

| Скрипт | Назначение |
|--------|------------|
| `00-bootstrap.sh` | Полный прогон всех шагов |
| `01-base-lan.sh` | LAN `192.168.1.1/24` (HA `192.168.1.41` без смены IP) |
| `02-install-podkop.sh` | Podkop (sing-box) |
| `03-config-podkop.sh` | VLESS Reality → VPS `193.233.232.48:8443` |
| `04-install-zapret2.sh` | DPI-обход (аналог nfqws2) |
| `05-wireguard-server.sh` | Удалённый доступ в LAN |
| `06-transmission.sh` | Торрент, окно 01:00–05:59 MSK |
| `07-router-tunnel.sh` | Reverse SSH → VPS `:6223` (для агента) |

---

## День 0 — до отключения Keenetic

1. Распакуйте Flint 2, подключите **только по кабелю** к ПК или в LAN Keenetic (параллельно).
2. Первый вход: `http://192.168.8.1` (stock GL.iNet).
3. Смените регион **CN → Global** (если нужно) — команды в [треде 4PDA](https://4pda.to/forum/index.php?showtopic=1080368).
4. Скачайте образ: [Firmware Selector → glinet_gl-mt6000 → 24.10.4 → sysupgrade](https://firmware-selector.openwrt.org/?version=24.10.4&target=mediatek%2Ffilogic&id=glinet_gl-mt6000).
5. **System → Flash firmware** → загрузить sysupgrade → **без сохранения настроек**.
6. После прошивки: `http://192.168.1.1` (или `192.168.8.1` до шага LAN), Wi‑Fi по умолчанию выключен — **только кабель**.

---

## День 1 — автонастройка одной командой

На роутере (SSH `root@192.168.8.1` или LuCI → Terminal):

```sh
curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh
```

Или по шагам:

```sh
export FLINT2_BASE=http://193.233.232.48:8789
for s in 01-base-lan 02-install-podkop 03-config-podkop 04-install-zapret2 05-wireguard-server 06-transmission 07-router-tunnel; do
  curl -fsSL "$FLINT2_BASE/$s.sh" | sh
done
```

После `01-base-lan` переподключите кабель — адрес станет `192.168.1.1`.

---

## День 2 — переключение с Keenetic

1. Запишите MAC/IP камер, HA (`192.168.1.41`) — они не меняются.
2. Отключите Keenetic от провайдера.
3. Кабель провайдера → **WAN Flint 2** (2.5G порт).
4. Проверьте интернет, YouTube, `https://sberbank.ru`.
5. С телефона (моб. интернет): импортируйте `phone.conf` из `/etc/wireguard/clients/` → откройте `http://192.168.1.41:8123`.

### Home Assistant

В **Настройки → Система → Сеть**:

- Локальный URL: `http://192.168.1.41:8123`
- Внешний URL: Tailscale `http://100.80.133.85:8123` или WireGuard

В `configuration.yaml` / packages:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 192.168.1.1
```

### Zapret2

LuCI → **Services → Zapret2** → пресет **МТС** (или ваш провайдер) → **Restart**.

---

## Доступ агента (Cursor) к роутеру

После `07-router-tunnel.sh` с VPS:

```sh
ssh -p 6223 root@127.0.0.1
```

Агент сможет донастраивать Flint 2 удалённо, как Keenetic через `:6222`.

---

## Откат

Stock GL.iNet: sysupgrade-образ с [dl.gl-inet.com](https://dl.gl-inet.com/router/mt6000/) — без сохранения настроек.

Keenetic: оставить неделю в коробке, кабель провайдера обратно на Keenetic.

---

## VPS: bootstrap-сервер

```sh
cd /root/projects/empire/scripts/flint2
python3 serve_bootstrap.py
# порт 8789
```

Проверка: `curl -sI http://193.233.232.48:8789/00-bootstrap.sh`
