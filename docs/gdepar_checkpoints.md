
## CP-20261022f — Прихожая invert + room contracts

**Диммер прихожей:** TS0052 on/off инвертирован в `empire_prihozhaya.yaml` (как `HA_DIMMER_INVERT.md`): 100%=raw off, off=raw on, dim=raw on+bri; template state учитывает dim.
**Контракты:** `docs/HA_ROOM_CONTRACTS.md` + `check_room_contracts` в `empire_ha_watcher.py` → state → блок в `empire_status_digest`.
**Проверено:** off/on100/on40 логика HA OK; watcher `room_contracts` OK.


## CP-20261022e — Ванная: свет не гаснет

**Баг:** `empire_vannaya_sensor_init` ставил **High** + timeout 60с; off ждал **3 мин** off — occupancy не сбрасывался.
**Фикс:** Medium + timeout 15с; off через **30 с** (как `HA_MOTION_DIMMER.md`). Применено live.
**Проверено:** presence off → через 30с свет off.


## CP-20261022d — Прихожая: новый TS0052 как диммер

**Устройство:** ZHA `a4:c1:38:f5:dd:6b:c4:68` → `light.tz3000_mgusv51k_ts0052_2` («Прихожая диммер»).
**Пакет:** `empire_prihozhaya.yaml` — template `light.empire_prihozhaya_svet` + motion SNZB-06P (как ванная).
**Ночь:** `binary_sensor.empire_prihozhaya_dim_night` 01:00–05:51 MSK → **40%** (ванна 20%); день 100%.
**Датчик:** тот же `binary_sensor.sonoff_snzb_06p_2`.
**Проверено:** presence→100%; night+presence→bri≈102; presence off 20s→off.


## CP-20261022c — S0 Armbian: soft-bugs + autoheal (без смены ОС)

**Позиция:** TOX1/Armbian Supervised остаётся; «сыпется» = кривые YAML/healer, не «купи железо».
**Софт-баги:**
- `empire_prihozhaya` / `empire_tualet_hobeian` / кухня: abort если target unavailable; retries 3–4 (было 8–12).
- Motion туалет/прихожая: condition «device available» перед вызовом скрипта.
- Flint healer: entity домофона `switch.smartintercom_otkryt_dver` (был вымышленный `accept_call`); chronic offline прихожей/SRW не триггерят reload ZHA/LocalTuya; MQTT reload если модуль пингуется, entity нет.
- HA watchdog: Mosquitto restart после старта HA / если домофон MQTT unavailable ≥3 мин (cooldown 30 мин); addon watchdog Mosquitto+Tailscale = True.
**Проверено:** config valid; healer `--check` END ok; Mosquitto restart → intercom entities сразу OK; offline script без spam в лог.
**Железо (ожидаемо offline):** zbeacon прихожая, SRW балкон.
**Backup:** `c0997d9f` → `/root/backups/ha/pre-stability-20261023-c0997d9f.tar`
**Не трогали:** Flint VPN/podkop/awg; HAOS на TOX1.


## CP-20261022b — HA full audit + cleanup

**Аудит:** HA API OK; ванная/туалет/кухня/домофон OK; Алиса Yaha loaded.
**Починено:** удалены 15 orphan automation/script (старый failsafe/watchdog spam, старый domofon_telegram); HA core restart.
**Железо (не софт):**
- Прихожая `light.zbeacon_ts0001_2` / template свет — Zigbee offline (питание/пара).
- Балкон SRW-TH01 — LocalTuya sleep/offline (кнопка на датчике).
**Не трогали:** Flint/VPN маршруты.


## CP-20261022 — Flint selfheal (LKG + flock + cron dedupe)

**Баг:** дубли crontab (×15) → параллельный `podkop start` → `duplicate rule-set tag: ai_awg-google_ai` → sing-box down → ТГ/ИИ мертвы; YouTube частично через zapret.
**Сделано:**
- `/usr/sbin/empire-singbox-lkg` — smoke/save/restore (golden, без podkop regenerate)
- `/usr/sbin/empire-cron-normalize` — один канонический crontab + `flock`
- lan-watch/watchdog: AI fix через LKG, не через шторм `36-ai`/`podkop restart`
- VPS: `empire-flint-remote-heal.timer` (каждые 5 мин, reverse `:6223`, алерт TG)
**Проверено:** FakeIP telegram/youtube/chatgpt/cursor; web.telegram.org 200; YT 204; cron 10 строк.


## CP-20261021 — Tailscale permanent + quiet HA TG

**Сделано:**
- Tailscale на Flint **постоянно** (`empire-tailscale-enable.sh`). Откат: `sh /usr/sbin/empire-tailscale-rollback.sh` (через reverse SSH :6223).
- Realtime HA spam в бот выключен: watchdog quiet, Flint `EMPIRE_HA_HEAL_TG=0`, vannaya offline-alert снят.
- Сводка дома: `empire-status-digest` **07:02 / 20:02 MSK** (+ блок «Дом / HA»).
- Диагностика по запросу: Telegram `/ha` → `script.empire_watch_diagnose_now`.

**Роутер TS:** http://100.84.251.64/

## CP-20261020b — Aeza Reality перенесён на :443

**Баг:** с домашнего IP `79.139.208.79` TCP на `138.124.90.47:8443` поднимался, ClientHello Reality резался. VDSina `:443` SNI `www.vk.com` и CF WebSocket с того же IP открывали YouTube и Telegram.
**Сделано:** на Aeza nginx stream SNI: сайты → `127.0.0.1:9443`, остальное → Xray Reality `127.0.0.1:4443` (SNI `www.vk.com`). `:8443` оставлен для Keenetic. Профили user01–20: вторая ссылка `138.124.90.47:443`. Сайты gdepar/neverretire/vpn — 200.
**Проверено с Flint:** user01 и user20, Aeza exit `138.124.90.47`, YouTube 204, web.telegram.org 200, Telegram DC `:80` 404. CF и VDSina — то же. Healthcheck ok=3.

## CP-20261020b — Aeza Reality перенесён на :443

**Баг:** с домашнего IP `79.139.208.79` TCP на `138.124.90.47:8443` поднимался, ClientHello Reality резался. VDSina `:443` SNI `www.vk.com` и CF WebSocket с того же IP открывали YouTube и Telegram.
**Сделано:** на Aeza nginx stream SNI: сайты → `127.0.0.1:9443`, остальное → Xray Reality `127.0.0.1:4443` (SNI `www.vk.com`). `:8443` оставлен для Keenetic. Профили user01–20: вторая ссылка `138.124.90.47:443`. Сайты gdepar/neverretire/vpn — 200.
**Проверено с Flint:** user01 и user20, Aeza exit `138.124.90.47`, YouTube 204, web.telegram.org 200, Telegram DC `:80` 404. CF и VDSina — то же. Healthcheck ok=3.

## CP-20261020b — Aeza Reality перенесён на :443

**Баг:** с домашнего IP `79.139.208.79` TCP на `138.124.90.47:8443` поднимался, ClientHello Reality резался. VDSina `:443` SNI `www.vk.com` и CF WebSocket с того же IP открывали YouTube и Telegram.
**Сделано:** на Aeza nginx stream SNI: сайты → `127.0.0.1:9443`, остальное → Xray Reality `127.0.0.1:4443` (SNI `www.vk.com`). `:8443` оставлен для Keenetic. Профили user01–20: вторая ссылка `138.124.90.47:443`. Сайты gdepar/neverretire/vpn — 200.
**Проверено с Flint:** user01 и user20, Aeza exit `138.124.90.47`, YouTube 204, web.telegram.org 200, Telegram DC `:80` 404. CF и VDSina — то же. Healthcheck ok=3.

## CP-20261020 — VPN: Telegram и DNS починены

**Баг:** телефон доходил до сервера, но DNS уходил на `172.19.0.2:853` (внутренний адрес Hiddify) и там пропадал. На VDSina приватные IP ещё и резались правилом `geoip:private`. На обоих Reality был `routeOnly: false` — Xray подменял адрес назначения, из‑за этого не открывался Telegram.
**Сделано:** `routeOnly: true` на VDSina и Aeza; исключение `172.19.0.2` → direct и DNAT на `1.1.1.1` (53 и 853), правило переживает ребут (`empire-vpn-dnsnat.service`, на VDSina ещё ufw `before.rules`). Профили user01–20: третья ссылка снова Cloudflare WebSocket с `alpn=http/1.1`. Healthcheck смотрит IP + YouTube 204 + Telegram 200.
**Проверено с Aeza и с Flint (домашний интернет в РФ):** все три входа, DNS на `172.19.0.2` отвечает, YouTube 204, web.telegram.org 200. Сайты gdepar/neverretire через фронт VDSina — 200.

## CP-20261019c — VPN audit, 20 users live

**Профили:** `/root/empire-secrets/profiles/user01.txt`…`user20.txt` = VDSina Reality + Aeza Reality + CF WebSocket. Сводный `user-profiles-01-20.txt`. Черновики в `profiles/drafts/` не раздавать.
**Проверено с Flint (РФ):** user01 и user20, все три входа, YouTube 204. UUID 01–20 есть на VDSina и на Aeza (Reality, WS, XHTTP).
**Снято:** публичная страница `/u1-k7m2p9/` со ссылкой user01.
**Healthcheck:** `empire-vpn-healthcheck.timer` каждые 30 мин, теперь проверяет WS (то, что в профилях), не XHTTP. Лог `/var/log/empire-vpn-health.log`. Telegram-алерта нет: файла `telegram.env` нет.
**JustHost** в профили не входит.

## CP-20261019b — VPN 20 users ready (VDSina+Aeza+CF)

**JustHost WAW1** `194.87.108.209`: Empire panel OK; **Flint RF blocked** → не в профилях.
**Профили:** см. CP-20261019c (было ошибочно записано как XHTTP).
**Healthcheck:** таймер жив; алерт в Telegram не подключён.

## CP-20261019 — CDN XHTTP Cloudflare `vpn.kalitkuprikroy.ru`

**Сделано:** зона CF Active; A `vpn`→`138.124.90.47` Proxied; LE на origin; Xray XHTTP `127.0.0.1:10088` path `/vless-xhttp-a7f3c91e2b/` mode `packet-up`; Cache Rule bypass; тест Empire+Flint → exit `138.124.90.47`.
**Секреты:** `/root/empire-secrets/cdn-kalitka/`.
**Профили:** третья ссылка CF — в urltest Flint; раздача user01–20 — по запросу.

# Контрольные точки

## CP-20261021 — Ванная свет + сломанный HA-watcher

**Симптом:** свет ванной горит, SNZB-06P (`binary_sensor.sonoff_snzb_06p`) unavailable с ~11:33 МСК.  
**Свет:** выключен вручную.  
**Баг хилера:** `empire_ha_watcher.DEFAULT_CRITICAL` был tuple → `.split` → AttributeError на каждом прогоне; HA-часть хилера **не работала**. Исправлено + `bath_light` auto-off если presence unavailable и свет on.  
**HA:** пакет `empire_vannaya_failsafe.yaml` (2 мин unavailable / 45 мин stuck on).  
**Ждёт:** кнопка на SNZB-06P ванной (Zigbee offline) — ZHA permit открыт.

## CP-20261017b — Климат NaN на wall

**Причина:** не MQTT. Балкон SRW-TH01 спит (LocalTuya); Детская/Семён ZHA offline с 4.10 / 23.09.  
**Сделано:** wall без NaN; шаблон балкона −40…60°C; ZHA permit+reconfigure.  
**17.10 ~11:00:** Семён online.  
**17.10 ~11:53:** Детская перепривязана (remove+permit) — **25.8°C / 40.6%**, батарея 100%. Семён **25.1°C**.  
**Балкон ещё ждёт:** SRW не в LAN; `.143` = Wifi Plug Кухня; Cloud 1106. Нужны кнопка на SRW + DHCP-резерв по MAC датчика.

## CP-20261017 — Домофон: TG+Алиса, трубка

**Сделано:** залипшие `Открыть`/`Курьер` на BlueStreak сброшены (глушили трубку); пакет `empire_domofon` — параллельно TG + TTS на все Yandex Station; автосброс залипания 15 мин; docs `HA_SMARTINTERCOM_MQTT.md` (почему трубка молчит).

**Ждёт владельца:** HA → Добавить интеграцию **Yandex Station** (QR) — без этого колонок нет, скрипт пишет уведомление в HA.

## CP-20261018d — Front сайтов VDSina `109.107.174.17`

**Прод front:** `109.107.174.17` (#1100095). Origin Aeza `138.124.90.47`.  
**Сделано:** UFW; xray 443→127.0.0.1:4443 (иначе Reality/VK съедал :443); nginx SNI; LE; `--resolve` gdepar/nr/par **200**.  
**DNS:** A → `109.107.174.17`, Cloudflare DNS only. Старые `89…` / `109.107.186.214` не использовать.

---

## CP-20261018b — Front на VDSina `89.124.76.215` (заменён)

Заменён на CP-20261018c (`109.107.186.214`).

---

## CP-20261018a — (устарело) план JustHost Vienna

JustHost #1276676 = VPN 3x-ui без root-консоли → фронт сайтов перенесён на VDSina (CP-20261018b).

---

## CP-20261014b — Cutover ОТМЕНЁН, остаёмся на 138.124.90.47

**Решение владельца:** не переезжать на `45.146.88.222`. Прод = **OLD `rough-beige` / 138.124.90.47**.

**Сделано:**
- NEW (`45…`): healer/gdepar/webapp/home-ops/amnezia **остановлены** (anti dual-run)
- OLD: healer timer, home-ops, flint bootstrap, gdepar/webapp **включены**
- cutover-скрипт на `:8789` → REFUSED; вместо него `restore-vps-138.sh`
- Amnezia Vienna (#1276676, `132.243.254.241:51821`) распарсена в `/root/empire-secrets/amnezia/` (не на публичном :8789)
- Корень домашнего обрыва: Flint reverse мёртв с **24.09**; HA Tailscale offline; PC TS+Amnezia мешали локальному `192.168.1.41`

**Ждёт на Flint (домашний Wi‑Fi):**
```sh
curl -fsSL http://138.124.90.47:8789/restore-vps-138.sh | sh
```

**Ждёт на Armbian (локально):**
```sh
curl -fsSL http://138.124.90.47:8789/ha_fix_tailscale_local.sh | bash
# или: docker restart app_a0d7b954_tailscale
```

**Amnezia на ПК:** импорт `vpn://` (Vienna) в приложении Amnezia; дома **не** гонять full-tunnel на LAN.  
**После :6223 на VPS:** `bash scripts/deploy_amnezia_vienna_via_reverse.sh`

---

## CP-20261014 — Cutover → 45.146.88.222 (ОТМЕНЁН → см. CP-20261014b)

**Причина:** IP `138.124.90.47` заблокирован РКН, Amnezia с дома не работает.

**Сделано на NEW (`causal-teal` / 45.146.88.222):**
- код/nginx/LE/systemd/env синкнуты; apps `gdepar/webapp` HTTP 200; healer timer enabled
- Amnezia server `amnezia-awg-flint` слушает **UDP 39182**
- home-ops :8767 up
- Tailscale установлен; ждёт клик логина (`tailscale up` / URL в чате)
- cutover-скрипт на `:8790`; Cursor example/ps1 → `45.146.88.222`
- на OLD (`138…`): empire timers + gdepar/webapp **остановлены** (anti dual-run); SSH оставлен

**Ждёт владельца (обязательно):**
1. Cloudflare origin A → `45.146.88.222` (neverretire/gdepar/…)
2. На Flint (домашний Wi‑Fi): `curl -fsSL http://45.146.88.222:8790/cutover-vps-45.146.88.222.sh | sh`
3. Cursor SSH → `HostName 45.146.88.222` (см. `deploy/cursor_ssh_config_pc.example`)
4. Кликнуть Tailscale login URL; сменить root-пароль (светился в чате)
5. После проверки — гасить nginx/удалить VPS `138.124.90.47`

 gdepar (ИИ-помощник и смежное)

Фиксация состояния без ожидания подтверждений. Git в проекте может отсутствовать — ориентир по дате и `GDEPAR_ASSET_VERSION`.

## CP-20260917e — Tailscale на NEW

**Сделано:** NEW `empire-vps` в tailnet: `100.124.148.18`; HA `100.80.133.85` ping+HTTP 200.
Cursor: `empire-vps-ts` → `100.124.148.18` (см. `deploy/cursor_ssh_config_pc.example`).

## CP-20260917d — Полный cutover OLD→NEW (138.124.90.47)

**Зачем не оставлять OLD:** dual healers/bots/таймеры дерутся; Flint туннель может смотреть не туда; Cursor на OLD правит уже не прод.

**Сделано:**

- Cloudflare origin уже бил в **NEW** (логи 104.23.*).
- Flint `/etc/flint2-tunnel/start.sh` → `VPS=138.124.90.47`; `:6223` на NEW; home-ops 200.
- Код хилера/HA-watcher/вехи синкнуты на NEW; `HA_URL` на NEW поправлен (был мёртвый `127.0.0.1:18123`).
- На OLD: остановлены empire-таймеры, app-сервисы, nginx. SSH оставлен для добивки/удаления в Aeza.
- HA с NEW: Tailscale таймаутится → fallback `home-ops checks.ha`.

**Сделать владельцу:**

1. Переподключить Cursor Remote SSH на `root@138.124.90.47` (сейчас сессия ещё на 193…).
2. Сутки ок → удалить OLD VIEs-3 в Aeza.
3. Опц. `tailscale up` на NEW (прямой HA API без fallback).
4. Metrika ID когда будет счётчик.

## CP-20260917c — Healer bugs fixed (timer, AWG peer, reverse SSH)

**Корневые баги:**

1. `empire-service-healer.timer` был **disabled/stopped** с 16.09 → хилер не бегал ~12ч.
2. AWG peer: искали `.3/.13` (stale), живой Flint — **`10.8.1.10`**; порог 180с давал ложный STALE.
3. Reverse `:6223`: на Flint `VPS=138.124.90.47` (чужой NEW), а Empire живёт на **`193.233.232.48`**; плюс `-R`+`-L` с `ExitOnForwardFailure` валил reverse, если `-L` не вставал.

**Исправлено:**

- timer enable + `SuccessExitStatus=0 1`; healer `return 0` (проблемы → state/digest).
- peer select: freshest among `10.8.1.10,10.8.1.13,10.8.1.3`; `EMPIRE_AWG_MAX_AGE` default 900.
- Flint `/etc/flint2-tunnel/start.sh`: VPS=193…, reverse-first; шаблон `scripts/flint2/flint2-tunnel-start.sh`.
- `empire-banya-weekly.timer` enabled.
- Прогон healer: **0 problems**, router channel=`reverse`, HA watcher OK.

## CP-20260917b — Healer architecture + HA watcher + no milestones bot

**Сделано:**

- Док: `docs/HEALER_ARCHITECTURE.md` (слои L0–L3, варианты A–D, HA мониторинг community).
- Вехи в утреннем TG **выкл.** (`EMPIRE_INSIGHTS_MILESTONES` default `0`).
- `scripts/empire_ha_watcher.py` — API + critical entities + Flint healer + HC ping; встроен в `empire_service_healer`.
- `docs/infra/SELF_HEAL.md` обновлён.

**Ждёт владельца:** `EMPIRE_HA_HC_PING_URL` (Healthchecks); Metrika ID.

## CP-20260917 — Quality weekly + healer NEW

**Сделано:**

- Парсинг бань **не чаще 1×/нед**: `empire-banya-weekly.timer` (вс ~07:30 МСК), `scripts/run_banya_weekly.sh` (nice/ionice).
- Daily digest/brief **без** блока бань; сводка — в `empire-weekly-report`.
- `main.py`: `banya_maps_daily` → no-op (force только с `BANYA_FORCE_DAILY=1`); weekly job + отчёт вс.
- Quality: ≥50 отзывов, телефон, свежесть отзывов ≤365д; `reviews_total` = Яндекс (не COUNT).
- Healer NEW: `docker_db` optional (SQLite); Flint peer `10.8.1.3`; SSH key на reverse :6223; `empire-home-ops`; HA fallback через home-ops.

**Нагрузка:** тяжёлый refresh остановлен; Playwright не крутится постоянно на 4GB.

**Ждёт владельца:** Tailscale login на NEW (для прямого HA API); Metrika ID.

## CP-20260909 — Каталог: offtopic + FLAGSHIP (MSK/MO/SPB/LO)

**Сделано:**

- `tools/banya_hide_offtopic.py` — скрытие VIP-саун / клубов саун / агрегатора «Сауны Питера» + сигналы из отзывов (не «девочки»=подруги).
- Прогон: **39** → hidden (в т.ч. 28× «Сауны Питера»); лог `data/gdepar_hide_offtopic_log.jsonl`.
- Шумные draft без URL (generic «Сауна»/«Баня») в FLAGSHIP: **~420** → hidden.
- Алиас регионов `FLAGSHIP` / `CAPITALS` = MSK,MO,SPB,LO в `tools/banya_regions.py`.
- Скрипт `scripts/run_flagship_banya.sh`; daily enrich/reviews приоритет FLAGSHIP; `reviews --region`.
- Дедуп отзывов: повторный `--show` = 0 групп (уже чисто после R6).
- Фон: enrich+OSM FLAGSHIP → `logs/banya_flagship.log`.

**Правила:** не прятать обычные «Сауна X»; не парсить Сибирь/ДВ ради объёма; цены/ёмкость — руками топ.

## CP-20260906 — Dual-flagship R6 (Pension + Gdepar)

**Сделано (VPS):**

- Карта EUROPE_URAL: **2045** published, **3261** draft, reviews **2108**, leads **2**, owners **0**.
- Phone top: SPB ~93%, MO ~86%, MSK ~61%; слабее PER/MUR/CU (~20%).
- Pension: дедуп статей (9 unique), `scripts/pension_site_sync.py`, timer `empire-pension-site-sync` daily 05:20 UTC, RSS `media/rss_pension.xml` (17 items с главами).
- Доки: `docs/audit/15_*` … `18_*`, вехи в `EMPIRE_PIPELINE_CHECKLIST.md`.

**Факт денег:** 0 ₽ выручки; Metrika оба сайта off; launch 15.09 → soft delay **01.11** (R6).

**Ждёт владельца:** оба счётчика Метрики; решение soft delay; YT yt-001; не жечь bridge на Директ.

**Контент Gdepar:** last-40 ≈ 20 монолог / 14 классика — сдвигать к гидам с UTM (`18_GDEPAR_CONTENT_MONEY_R6.md`).

## CP-20260829 — Издательство (посты без ИИ)

**Сделано:** оболочка `/admin/studio` на gdepar и neverretire: слоты, заливка `.md`/`.txt`, матрица CSV, календарь. Режим **тест** (в TG не шлёт). Журнал сайта: `/journal`. Док: `docs/publisher_studio.md`. Тесты: `tests/test_publisher.py`.

**Проверка:**

```bash
EMPIRE_SKIP_EMBEDDINGS=1 ./venv/bin/python -m publisher demo
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8001/admin/studio/login
curl -sS http://127.0.0.1:8001/journal | head
```

**Ждёт владельца:** потыкать UI; живой режим — только после `EMPIRE_PUBLISHER_LIVE=1`.

## CP-20260520 — ТЗ без участия владельца (кроме Метрики)

**Сделано:**

- Помощник «Пар?»: заглушка, LLM 25%, кэш, RL, RAG, стриминг SSE (`/api/gdepar/assistant/stream`).
- Саммари попапа: LLM 100% при наличии `OPENROUTER_API_KEY`.
- Виджет: z-index над картой, подпись «Помощник», cookie `gdepar_asst_sid`, логи `timing` + `session_id`.
- Health: `GET /api/gdepar/health` — флаги assistant/popup_summary/metrika.
- Документация: ТЗ §7 решения, `metrika_goals_setup.md`, nginx stream без буферизации.
- Тесты: `pytest tests/` (59+), деплой `scripts/deploy_gdepar.sh`.

**Ждёт владельца:**

- `YANDEX_METRIKA_ID` и создание JS-целей в кабинете Метрики.
- Чеклист напоминаний: **`docs/REMINDERS_gdepar.md`** (4 пункта + мастер-ТЗ).

**Вне репозитория:**

- p95-алерты в Grafana/хостинге (смотреть `journalctl -u empire_gdepar | grep timing`).

**Проверка после выката:**

```bash
curl -s http://127.0.0.1:8001/api/gdepar/health | python3 -m json.tool
curl -sS -X POST http://127.0.0.1:8001/api/gdepar/assistant/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"баня","page":"home"}' | head
```

`GDEPAR_ASSET_VERSION=20260520b`

## CP-20260621 — B2B MVP + OSM EUROPE_RU

**Сделано:**

- MVP-схема БД: `tools/banya_schema_mvp.py` — цены, вместимость, `banya_leads`, `banya_owner_accounts`, `seo_landings`.
- Лиды: `POST /api/banya/lead` (phone_reveal, whatsapp, booking_request, map_click); телефон скрыт в API до клика.
- UI: `static/gdepar/lead.js` — «Показать телефон» на карте и карточке бани.
- B2B: `/partners` + ссылка в навигации.
- Регионы: `EUROPE_RU` (56) + `URAL`/`SIB`/`FAR_EAST` → alias `RU_ALL` (~83) в `tools/banya_regions.py`.
- Парсинг: `./scripts/run_osm_europe_ru.sh` или `./scripts/run_osm_ru_all.sh [RU_ALL|URAL|SIB|…]` → только `draft` (retry Overpass 429, зеркало kumi).

**Следующий шаг (не блокер):**

- После OSM: `yandex_scrape.py enrich` по MO, MSK, SPB.
- Owner dashboard, premium-сортировка, SEO-лендинги — по мастер-ТЗ.

**Проверка:**

```bash
tail -f logs/osm_europe_ru.log
curl -s http://127.0.0.1:8001/partners | head
curl -sS -X POST http://127.0.0.1:8001/api/banya/lead \
  -H 'Content-Type: application/json' \
  -d '{"spot_id":1,"lead_type":"phone_reveal","source":"test"}' | python3 -m json.tool
```

## CP-20260719 — OSM RU_ALL (draft only)

**Сделано:**

- Реестр `tools/banya_regions.py`: **83** кода (`EUROPE_RU` + `URAL` + `SIB` + `FAR_EAST`, alias `RU_ALL`).
- OSM-парсер усилен: больше тегов, name/city fallback, alt ISO для CR/SEV, name-area для KUR, retry упавших, commit по региону.
- Прогон gaps+восток: `logs/osm_expand_east.log` → **~1626** новых draft, **83** региона в БД; **published без изменений** (карта не тронута).
- Скрипт: `./scripts/run_osm_ru_all.sh [RU_ALL|URAL|SIB|…]`.

**Не делать сразу:** массовый pubauto по новым регионам без Yandex enrich.

## CP-20261022 — Unkillable VPN 20: 3 Reality + CDN

**Профили:** `/root/empire-secrets/profiles/user01..20` = CF-WS + VDSina Reality + Aeza Reality + JustHost STO1 Reality (urltest JSON + base64 sub).
**Подписка:** tokenized `/sub/<token>/userNN` на `vpn.kalitkuprikroy.ru` (TOKEN в `cdn-kalitka/sub-meta.json`); legacy `/vpn-profile-k7m2p9/`.
**STO1:** 20 UUID (как VDSina) на Reality dest=www.vk.com.
**Healthcheck:** 4 ноги (vds/aeza/sto1/cdn), xray 26.7.28 в `/usr/local/lib/empire-xray/`, TG через `empire_notify.py`.
**Приёмка:** user01+user20 все 4 входа YT204/TG200. Flint AI/awg не трогали. Раздачу юзерам не делали.
**Доки:** `docs/VPN_20USERS_HIDDIFY_RU.md`, `profiles/IMPORT_HIDDIFY.txt`.

## 2026-10-22 JustHost STO1
- Reality dest=www.vk.com works; added to Flint urltest (4 nodes); smoke YT/TG OK; panel pass rotated in empire-secrets.

## CP-20261031 — Primary VPN → VDSina `89.124.64.70`

**Сделано:** новый VDSina (3x-ui) стал основным:
- Amnezia AWG `39182/udp` перенесён с Aeza (`amnezia-awg-flint` там stopped); Flint `awg0` Endpoint → `89.124.64.70:39182`, handshake OK
- VLESS Reality `www.vk.com` + Vision; nginx SNI `:443` → sites `:8443` / xray `:4443`; 20 users + `flint-router`
- podkop `main` urltest: VDSina-Flint = новый IP; YT204 / TG200 с Flint
- Сайты через `--resolve` на новый IP = 200 (self-signed до смены CF A / issue-certs)

**Ждёт владельца:** Cloudflare A (DNS only) origin → `89.124.64.70`, затем `bash /root/justhost-site-front/issue-certs.sh` на VPS. Старый `109.107.174.17` не использовать.

**Секреты:** `/root/empire-secrets/vdsina-89/`, профили user01–20 обновлены (нога VDSina).
