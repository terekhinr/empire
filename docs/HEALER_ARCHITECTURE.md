# Empire: архитектура хилеров и контроль HA

Исследование (2026-09) + варианты для нашего стека (VPS + Flint + HA).

## 1. Как устроены похожие хилеры у людей

### Слои (не один «бог-скрипт»)

| Слой | Где живёт | Что ловит | Типичные инструменты |
|------|-----------|-----------|----------------------|
| **L0 OS** | тот же хост | hung process, OOM, unit down | systemd `Restart=`, `WatchdogSec` + `sd_notify`, StartLimitBurst |
| **L1 local healer** | тот же хост / LAN | API 500, entity unavailable, залипший sensor | cron/timer скрипты, router watchdog |
| **L2 active probe** | *другая* машина | DNS/TLS/proxy/сеть | Uptime Kuma HTTP/TCP/keyword |
| **L3 dead-man's switch** | облако | хост мёртв, cron не бежал, монитор молчит | Healthchecks.io / Kuma Push / UptimeRobot |

Ключевой принцип сообщества: **хилер на той же сети не узнает, что упал интернет/электричество**. Поэтому L2/L3 ставят вне дома (дешёвый VPS или SaaS).

### Надёжность — правила, которые все повторяют

1. **Cooldown + daily/hourly cap** — не крутить restart в цикле.
2. **Heal только после подтверждения** (2–3 fail подряд / retries в Kuma).
3. **Эскалация**: soft (reload integration) → hard (restart core) → notify human.
4. **Who watches the watcher**: Kuma/healer пингует Healthchecks; если молчит — SMS/email снаружи.
5. **Разделение probe и fix**: probe с VPS, fix на Flint/HA по LAN (иначе нельзя починить при мёртвом WAN, и наоборот — нельзя увидеть мёртвый WAN из дома).

### Что именно чинят

- systemd unit / docker container down → `systemctl restart` / `docker restart`
- HTTP health ≠ 200 → restart app (+ rollback если StartLimit)
- HA API down → `ha core restart` (редко)
- ZHA/Tuya entities `unavailable` → reload config entry (часто)
- Occupancy/light stuck → domain-specific automation (наш Flint HA-healer)
- Tunnel/VPN peer stale → rekey / kick reverse SSH
- Cron/backup silence → dead-man alert (чинить руками; автохилер тут слабый)

---

## 2. Варианты хорошего «чинит всё» для Empire

### Вариант A — **федерация локальных хилеров** (рекомендуем, уже почти так)

```
┌──────────── VPS ────────────┐     ┌──────── Flint ────────┐     ┌── HA ──┐
│ empire-service-healer       │────▶│ empire-flint-watchdog │────▶│ API    │
│  · nginx/fastapi/sqlite     │:6223│  · zapret/amnezia/usb │ LAN │ entities│
│  · reverse SSH / digests    │◀────│ empire-ha-healer      │◀────│        │
│ empire-ha-watcher (deep)    │     │  · ZHA/Tuya/occupancy │     └────────┘
│ empire-router-watchdog      │     └───────────────────────┘
└────────────┬────────────────┘
             │ push /fail
             ▼
      Healthchecks.io (L3)
```

Плюсы: каждый узел чинит то, до чего дотягивается; нет единого SPOF в коде.  
Минусы: нужна общая сводка (у нас — morning/evening digest + service-healer state).

**Статус Empire:** A уже в проде; HA deep-check — `scripts/empire_ha_watcher.py`, встроен в `empire_service_healer`.

### Вариант B — **один оркестратор + агенты**

Один процесс на VPS (`empire-omni-healer`) шлёт RPC агентам на Flint/HA.  
Плюсы: единый отчёт. Минусы: если VPS/туннель мёртв — агенты должны уметь жить сами (иначе хуже A). Для нас избыточно.

### Вариант C — **VPS Kuma + Flint healer + HC**

- Uptime Kuma на VPS: HTTP neverretire.ru, HA API via Tailscale, Flint home-ops.
- Flint: текущие healers без изменений.
- Healthchecks: heartbeat от service-healer и от HA automation раз в N минут.

Плюсы: красивые графики, retries из коробки. Минусы: ещё один сервис; дублирует часть healer.

**Рекомендация:** остаёмся на **A**, добавляем **C-lite** (только Healthchecks ping из healer, без полного Kuma, пока не заболит).

### Вариант D — «бог на роутере»

Всё на Flint. Плохо: Flint не видит публичный DNS/TLS Empire; при падении WAN нет внешнего алерта.

---

## 3. Контроль HA у большинства пользователей

### Что используют

| Инструмент | Роль |
|------------|------|
| **Uptime Kuma** (часто на отдельной Pi/VPS) | HTTP check `GET /api/` с Bearer + keyword; Telegram/ntfy |
| **Healthchecks.io / Kuma Push** | dead-man: HA automation / backup cron пингует URL |
| **Watchman** (HACS) | YAML/dashboard: missing/unavailable entities → sensor |
| **Spook** (HACS) | Repairs: битые ссылки в automations/dashboards |
| **Встроенный System Health + Repairs** | диск recorder, broken integrations |
| **Glances / Netdata / Grafana** | host metrics, не логика HA |
| **ntfy / Telegram / Gotify** | доставка алертов |

### Эффективное использование

1. **Не пинговать ICMP хоста** — HA может быть wedged при живом ядре. Только authenticated `/api/` (+ опционально `/api/config`).
2. **Retries 2–3** в мониторе — отсечь Wi‑Fi blips.
3. **Critical entities list** (домофон, свет ванны, presence) — алерт/heal только по ним, не по всем `unavailable` (шум от солнечных инверторов и т.п.).
4. **Watchman/Spook** — раз в сутки/на reload конфига; не путать с realtime uptime.
5. **Dead-man из HA**: automation каждые 10–15 мин → `rest_command` ping HC. Если HA или интернет дома умерли — внешний алерт.
6. **Heal на LAN (Flint)**, **probe с VPS** — наш текущий паттерн.

### Варианты для Empire

| # | Что | Effort | Эффект |
|---|-----|--------|--------|
| **E1** | `empire_ha_watcher` на VPS (уже) + Flint `empire-ha-healer` | done | liveness + soft heal |
| **E2** | `EMPIRE_HA_HC_PING_URL` → Healthchecks | 10 мин | who-watches-watcher |
| **E3** | Kuma на VPS: 5 мониторов (sites + HA + home-ops) | 1–2 ч | UI/история |
| **E4** | HACS Watchman + Spook на HA | 30 мин | config hygiene |
| **E5** | HA automation dead-man ping | 20 мин | ловит «HA молчит» |

Предпочтение: **E1+E2+E5**, Kuma (E3) — по желанию.

---

## 4. Что у нас в коде

| Компонент | Путь | Где крутится |
|-----------|------|--------------|
| Полный стек-хилер | `scripts/empire_service_healer.py` | VPS timer ~5 мин |
| HA watcher/healer | `scripts/empire_ha_watcher.py` | вызывается из service-healer; можно `--check` отдельно |
| HA device healer | `scripts/flint2/empire-ha-healer/` | Flint каждые 5 мин |
| Flint watchdog | `scripts/flint2/empire-flint-watchdog/` | Flint |
| Router watchdog | `scripts/empire_router_watchdog.py` | VPS |

### ENV для HA watcher

```
HA_URL=…
HA_TOKEN=…
EMPIRE_HA_LAN_URL=…          # опц. через туннель
EMPIRE_HA_SSH=root@…
EMPIRE_HA_CRITICAL_ENTITIES=binary_sensor.…,light.…
EMPIRE_HA_HC_PING_URL=https://hc-ping.com/<uuid>
EMPIRE_HA_WATCH_DRY=1
```

### Ручной прогон

```bash
./venv/bin/python scripts/empire_ha_watcher.py --check
./venv/bin/python scripts/empire_service_healer.py   # включает HA watcher
```

---

## 5. Напоминания бота про вехи

Выключены по умолчанию: `EMPIRE_INSIGHTS_MILESTONES=0` в `planning_insights.py`.  
Включить снова: `EMPIRE_INSIGHTS_MILESTONES=1` в `.env` + restart сервиса брифинга.
