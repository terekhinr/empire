# Flint 2: YouTube и блокировки РФ — два режима

Роутер: **GL.iNet GL-MT6000 (Flint 2)**  
Прошивка: **vanilla OpenWrt 24.10.x** (не stock GL.iNet)  
Дата сборки гайда: 2026-08-28

Это не «свой велосипед», а склейка профильных решений. Empire-скрипты только ставят их неинтерактивно, держат сторож и переключают режимы.

---

## Откуда схема (обязательно прочитать)

| Источник | Зачем |
|----------|--------|
| [OpenWrt wiki GL-MT6000](https://openwrt.org/toh/gl.inet/gl-mt6000) | Только **sysupgrade** vanilla OpenWrt. Stock GL ломает firewall. |
| [GL.iNet forum: Zapret not work on Flint 2](https://forum.gl-inet.com/t/zapret-not-work-on-flint-2/66798) | Hardware offload / Network Acceleration обходит nfqws. |
| [remittor/zapret-openwrt](https://github.com/remittor/zapret-openwrt) | Пакеты zapret для OpenWrt, LuCI, `update-pkg.sh`. |
| [zapret-openwrt #790](https://github.com/remittor/zapret-openwrt/issues/790) | Flow offloading = fast path **мимо** netfilter → DPI снова видит SNI. |
| [zapret-openwrt #412](https://github.com/remittor/zapret-openwrt/issues/412) | На GL-MT6000 IPv6 (в ЛК провайдера) ломает Discord/обход. |
| [zapret-openwrt #723](https://github.com/remittor/zapret-openwrt/discussions/723) | На stock GL нет `kmod-nft-queue`. На vanilla 24.10 пакет есть в opkg. |
| [StressOzz/Zapret-Manager](https://github.com/StressOzz/Zapret-Manager) | Подбор стратегии `zms` (v1–v9, Flowseal, тест YouTube). |
| [podkop](https://github.com/itdoginfo/podkop) · [документация](https://podkop.net/docs/install/) | Маршрутизация доменов в VLESS/VPN на OpenWrt 24.10. |
| [podkop settings](https://podkop.net/docs/settings/) | Disable QUIC, Don’t Touch DHCP, source `br-lan`. |
| [podkop sections](https://podkop.net/docs/sections/) | `russia_inside` **не** содержит Telegram; Meta/Discord **подсети** — отдельные списки. |
| [podkop diagnostics](https://podkop.net/docs/diagnostics/) | FakeIP-проверка **падает**, если тот же трафик режет zapret/byeDPI. |
| [podkop FAQ](https://podkop.net/docs/faq/) | Звонки TG/Discord: доп. списки + выключить P2P в приложении. |
| [4PDA: обход на OpenWrt](https://4pda.to/forum/index.php?showtopic=1085698) | zapret по Wi‑Fi vs LAN, podkop как следующий шаг. |

Два разных инструмента:

- **Zapret** — не VPN. Пакеты идут на WAN провайдера. `nfqws` портит ClientHello так, что ТСПУ не узнаёт YouTube.
- **Podkop** — VPN/прокси. YouTube получает FakeIP `198.18.x` и уезжает в VLESS на ваш сервер.

Их **нельзя** натравить на один и тот же домен одновременно: podkop Diagnostics → «Прокси-трафик через FakeIP» станет красным.

---

## Что выбрать

```
Нужен Empire VPS (193.233.232.48:8443)?
        │
        ├─ ДА  → режим A (VPS): YouTube/TG/Meta → VLESS
        │         zapret живёт как страховка и failover
        │
        └─ НЕТ → режим B (без VPS): YouTube/TG → zapret
                  ChatGPT и т.п. zapret не спасёт (гео блок) —
                  нужен любой свой VPN/Amnezia, не обязательно Empire.
```

| | Режим A — с VPS | Режим B — без VPS |
|--|-----------------|-------------------|
| YouTube, TikTok, Instagram | VLESS (список `russia_inside`) | zapret + хостлист |
| Telegram | VLESS + список `telegram` | zapret (хуже звонков) |
| ChatGPT / Claude | секция `ai_awg` → Amnezia | только если есть свой awg0 |
| Торрент-сайты | FakeIP + VLESS | zapret, пиры как есть |
| Зависимость от VPS | да | нет |
| Ломается после обновления ТСПУ | редко (туннель) | часто → `zms` новая стратегия |
| Сторож | Flint + опционально VPS | только Flint |

---

## Общие условия (оба режима)

Без этого zapret на Flint 2 «ставится, но не работает» — это самый частый тред.

1. **Прошивка** — vanilla OpenWrt 24.10 sysupgrade, **без** сохранения stock-настроек.  
   [Firmware Selector → glinet_gl-mt6000](https://firmware-selector.openwrt.org/?version=24.10.4&target=mediatek%2Ffilogic&id=glinet_gl-mt6000)
2. **Flow offloading = выкл.** LuCI → Network → Firewall → Routing/NAT Offloading: Software **и** Hardware Off.  
   Иначе CPU не видит пакеты, nfqws бесполезен.
3. **IPv6 = выкл.** на WAN/LAN роутера. Если в ЛК провайдера включён IPv6 — выключить и там.
4. **QUIC (UDP 443) режется** с LAN. Иначе Android YouTube уходит в QUIC, TCP-desync его не касается.
5. **На клиентах выключить** Amnezia / свой VPN / DoH в браузере (Chrome «безопасный DNS»).
6. **AdGuard Home** (если стоит): не перехватывать DNS клиентов до Flint — иначе пакеты не доходят до nft.

Это делает скрипт `19-prereq-dpi.sh`.

---

## Режим B — без VPS (zapret)

### Как это работает

```
Телефон/ПК
    │ DNS :53  →  Flint dnsmasq (8.8.8.8 / 1.1.1.1), не DNS провайдера
    │ HTTPS    →  WAN напрямую
    ▼
Flint nft: DROP UDP/443 (QUIC)
      nft: NFQUEUE → процесс nfqws
           nfqws подменяет TLS ClientHello (стратегия)
    ▼
Провайдер видит «не youtube» → пускает
YouTube отвечает → смотрите видео
```

IP Google не прячется. Если провайдер режет **по IP**, zapret бессилен — нужен режим A.

### Установка с USB (VPS не нужен даже для скачивания скриптов)

На машине с клоном Empire:

```bash
sh /root/projects/empire/scripts/flint2/pack-usb-novps.sh
# каталог /tmp/flint-novps-usb → на флешку
```

На Flint:

```sh
# путь к флешке посмотрите: block info  /  ls /mnt
sh /mnt/usb/flint-novps-usb/00-bootstrap-novps.sh
```

Скрипт по очереди:

1. `01-base-lan.sh` — LAN `192.168.1.1` (если ещё не)
2. `19-prereq-dpi.sh` — offload, IPv6, `kmod-nft-queue`
3. `04-install-zapret2.sh` — официальный `update-pkg.sh` с GitHub remittor
4. `22-configure-zapret.sh` — хостлист + DROP QUIC
5. `21-mode-novps.sh` — стоп podkop (YouTube не в мёртвый VLESS), DNS 8.8.8.8
6. `install-local.sh` — сторож на cron

Если GitHub с роутера не качается (`Could not resolve host: raw.githubusercontent.com`):

```sh
echo "nameserver 8.8.8.8" > /tmp/resolv.conf
echo "185.199.108.133 raw.githubusercontent.com" >> /etc/hosts
```

(типовой совет из issues Zapret-Manager).

### Подбор стратегии (обязательно, если дефолт не берёт YouTube)

На Flint, интерактивно:

```sh
wget -O /tmp/Zapret-Manager.sh https://raw.githubusercontent.com/StressOzz/Zapret-Manager/main/Zapret-Manager.sh
sh /tmp/Zapret-Manager.sh
```

Дальше команда `zms` → пункт теста стратегий **для YouTube**. Скрипт Empire стратегию сам не крутит: то, что вчера работало на МТС, завтра ломает Ростелеком.

LuCI: **Services → Zapret** — там же хостлист и NFQWS_OPT.

### Проверка

```sh
/usr/sbin/empire-flint-watchdog --check
curl -I --max-time 15 https://www.youtube.com/generate_204
pgrep -a nfqws
uci get firewall.@defaults[0].flow_offloading   # 0
```

С телефона: Wi‑Fi Destroy, VPN выкл, YouTube.

---

## Режим A — с VPS (podkop + VLESS)

### Как это работает

```
Клиент спрашивает DNS youtube.com
    ▼
dnsmasq → 127.0.0.42 (это включает сам podkop, «Don't Touch DHCP» = нет)
    ▼
sing-box отдаёт FakeIP 198.18.x.x
    ▼
Клиент шлёт TCP на 198.18.x → nft PodkopTable redirect :1602
    ▼
sing-box outbound VLESS Reality → 193.233.232.48:8443
    ▼
VPS ходит на YouTube «как Европа»
```

Провайдер видит только TLS на ваш VPS, не SNI youtube.

Telegram **не** входит в `russia_inside` — отдельный community list (документация podkop).  
ChatGPT в `russia_inside` есть: чтобы слать его в Amnezia, нужна **другая секция** `ai_awg` (тип VPN, интерфейс `awg0`), а домены AI убираются из main через свой список — так и сделано в `03-config-podkop.sh` / `14-podkop-ai-telegram.sh`.

### Установка (роутер уже в домашней сети, VPS жив)

```sh
curl -fsSL http://193.233.232.48:8789/00-bootstrap.sh | sh
```

Порядок внутри:

1. `19-prereq-dpi.sh`
2. `01-base-lan.sh`
3. `02-install-podkop.sh` — официальный `install.sh` itdoginfo, удаляет `https-dns-proxy`
4. `03-config-podkop.sh` — UCI: VLESS URL, `russia_inside`+`telegram`, QUIC off, списки качать через прокси
5. `04-install-zapret2.sh` + `22-configure-zapret.sh` — zapret для failover
6. туннель, Keenetic snapshot, verify

Сторож с VPS:

```bash
bash /root/projects/empire/scripts/flint2/empire-flint-watchdog/install.sh
```

Переключить уже настроенный роутер:

```sh
curl -fsSL http://193.233.232.48:8789/20-mode-vps.sh | sh
# или
curl -fsSL http://193.233.232.48:8789/21-mode-novps.sh | sh
```

### Диагностика (официальная, не Empire)

LuCI → **Services → Podkop → Diagnostics → запустить**.  
Должны быть зелёные: DNS, sing-box ≥ 1.12.4, **автостарт sing-box выключен**, таблица PodkopTable, FakeIP, outbound delay.

Если FakeIP красный и у вас включён zapret на те же домены — это ожидаемо по доке. В режиме A YouTube в FakeIP, zapret их не обрабатывает (198.18.x).

```sh
curl -I https://www.youtube.com/generate_204
nslookup youtube.com 127.0.0.1   # 198.18.* = FakeIP, значит podkop жив
```

---

## Сторож (watchdog)

Два уровня. ИИ не участвует.

### 1. На Flint — главное

| Что | Когда | Файл |
|-----|--------|------|
| Быстрый datapath | каждую минуту | `empire-lan-watch.sh` |
| Полная проверка + починка | каждые 5 мин | `/usr/sbin/empire-flint-watchdog` |
| Failover VLESS→zapret | из полного прогона | `/usr/sbin/empire-vless-failover` |

**Режим B (`novps`):** жив ли `nfqws`, выключен ли offload, hijack :53, YouTube `generate_204`. Podkop/туннель VPS не трогает.

**Режим A (`vps`):** sing-box, nft :1602, zapret, DNS, YouTube, Telegram, FakeIP трекеров, awg0, reverse SSH.

**Failover (только A):** два цикла подряд «TCP на VPS:8443 нет **и** YouTube мёртв» → с UCI снимаются `community_lists`, podkop перезапускается, YouTube идёт в WAN + zapret. Когда :8443 снова отвечает два цикла — списки возвращаются. Файл состояния: `/etc/empire/bypass-state` (`vps` / `failover`).

Cooldown 15 мин на повторный рестарт одного сервиса (`--force` сбрасывает).

Лог: `/tmp/empire-flint-watchdog.log`  
Ручной прогон: `empire-flint-watchdog --check` или `--force`  
PWA: `http://192.168.1.1/empire/`

### 2. На VPS — второй контур (только режим A)

`empire-router-watchdog.timer` каждые 15 мин: SSH на Flint через `:6223` или через HA Tailscale, при подтверждённом сбое — `13-fix-all.sh`.  
Без reverse-туннеля этот контур молчит; локальный сторож на Flint продолжает работать.

---

## Как устроены скрипты

Все лежат в `scripts/flint2/`. На Flint качаются с `http://193.233.232.48:8789/` (процесс `serve_bootstrap.py`) **или** копируются с USB.

### `19-prereq-dpi.sh`

Выключает `firewall.@defaults[0].flow_offloading` и `_hw`, IPv6 на wan/lan, ставит `kmod-nft-queue`, снимает `https-dns-proxy`. Без этого шага zapret на MT6000 часто «есть процесс, нет эффекта».

### `04-install-zapret2.sh`

Качает официальный `update-pkg.sh` ветки `zap1` remittor (пакет **zapret**, с ним живёт Zapret-Manager). Если уже стоит zapret/zapret2 — только restart. Стратегию не затирает.

### `22-configure-zapret.sh`

Пишет `zapret-hosts.txt` в `/opt/zapret/ipset/zapret-hosts-user.txt`, вешает постоянный DROP UDP/443 lan→wan, включает `MODE_FILTER=hostlist` только если было `none`. **Не** переписывает `NFQWS_OPT` — это зона `zms`.

### `02-install-podkop.sh`

Официальный `install.sh` itdoginfo (через файл, не bash `<( )` — на ash OpenWrt его нет). Снимает https-dns-proxy и Getdomains. Отключает autostart `sing-box` (иначе диагностика podkop красная).

### `03-config-podkop.sh`

Чистый UCI по доке: main = proxy URL VLESS, списки `russia_inside`+`telegram`, `disable_quic=1`, `dont_touch_dhcp=0`, `download_lists_via_proxy=1`, секция `ai_awg` тип vpn. Пишет `/etc/empire/bypass-mode=vps`. Конфиг sing-box **не** редактирует руками — его генерирует podkop.

### `20-mode-vps.sh` / `21-mode-novps.sh`

Переключатели. Novps: стоп podkop (или оставляет только `ai_awg`), DNS 8.8.8.8, выключает reverse SSH cron.

### `00-bootstrap.sh` / `00-bootstrap-novps.sh`

Оркестраторы «с нуля». Novps умеет работать **без** `FLINT2_BASE`, если файлы лежат рядом (USB).

### `pack-usb-novps.sh`

Собирает `/tmp/flint-novps-usb` для флешки.

### Сторож

| Файл | Роль |
|------|------|
| `empire-flint-watchdog` | Проверки `ok_*`, фиксы `fix_*`, учёт режима |
| `mode-lib.sh` → `/etc/empire/mode-lib.sh` | `vps`/`novps`, TCP-проба VPS, offload |
| `vless-failover.sh` | Снятие/возврат community lists |
| `empire-lan-watch.sh` | Каждую минуту: в novps только nfqws+DNS; в vps — :1602 и дубли sing-box |
| `empire-lan-fix.sh` | Только режим A: nft :1602, DoH block, mark 0x200000. В novps не зовётся из lan-watch |
| `install.sh` | Заливка через reverse SSH с VPS |
| `install-local.sh` | Копирование с USB/каталога на сам Flint |
| `cgi/empire-api` | JSON для PWA, поле `mode` |

`13-fix-all.sh` — тяжёлая «аптечка» с VPS (пакеты, USB, Samba, Amnezia, туннель). Сторож Flint вызывает её только через VPS-watchdog, не каждую минуту.

---

## Типичные поломки (из тех же веток)

| Симптом | Что проверить |
|---------|----------------|
| YouTube только на Wi‑Fi, по кабелю нет | Offload; правила nfqws на `br-lan`, не только wlan; Windows checksum offload |
| Всё есть, Discord Checking updates | IPv6 в ЛК провайдера; список `updates.discord.com`; в режиме A — community Discord |
| Zapret не ставится, нет kmod-nft-queue | Вы не на vanilla 24.10, а на stock GL — см. discussion #723 |
| Podkop Diagnostics FakeIP ✗ | На клиенте VPN/DoH; или zapret режет те же домены; или sing-box автостарт включён |
| После ребута «старый» YouTube | FakeIP TTL; подождать минуту или сбросить DNS на клиенте |
| `zms` / wget GitHub Operation not permitted | DNS роутера, hosts для raw.githubusercontent.com |
| Gemini/ChatGPT при живом YouTube | Это гео, не DPI: нужен awg0 или VLESS, не zapret |

---

## Файлы режима на роутере

```
/etc/empire/bypass-mode     vps | novps
/etc/empire/bypass-state    vps | failover | novps
/etc/empire/vps.env         VPS_HOST / VPS_PORT
/etc/empire/mode-lib.sh
/etc/empire-flint-ui.token
```

Вернуться с failover на VPS вручную: снова выполнить `03-config-podkop.sh` или `20-mode-vps.sh`.

---

## Связанные документы

- Домашняя схема: `docs/infra/HOME_NETWORK.md`
- Миграция Keenetic: `docs/FLINT2_SETUP.md`
- Админка без ИИ: `docs/infra/FLINT_ADMIN_NO_AI.md`
- Телефон без VPS (Tailscale): `docs/infra/PHONE_ACCESS_NO_VPS.md`
