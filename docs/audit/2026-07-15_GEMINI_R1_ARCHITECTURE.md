# Gemini R1 · Архитектура VPS + дом (2026-07-15)

Ответ Gemini на промпт 1 из `GEMINI_AUDIT_PROMPTS.md`.  
Сверка с фактическим состоянием Empire — что уже есть, что взять в работу.

---

## Что Gemini описал верно

| Элемент | Факт в Empire |
|---------|---------------|
| VPS 4/8 + сайты + TG + VPN | ✅ `docs/infra/ARCHITECTURE.md` |
| Flint OpenWrt + podkop/zapret/Amnezia | ✅ `HOME_NETWORK.md`, `router-watchdog` |
| Tailscale VPS ↔ HA | ✅ 100.84.19.35 ↔ 100.80.133.85 |
| Бэкап → Я.Диск | ✅ `vps_backup_to_yandex.sh`, audit sync |
| SPOF «VPS упал — алерта нет» | ✅ верно; watchdog внутри VPS не поможет |

---

## SPOF: рекомендации Gemini vs наш статус

| SPOF | Gemini | У нас сейчас | Действие |
|------|--------|--------------|----------|
| **VPS** | IaC, деплой <15 мин, конфиги вне VPS | `vps_restore_from_yandex.sh`, runbook 1–3 ч, `/etc/empire` на Диске | ✅ база есть. Ускорить: один `deploy_empire_infra.sh` после restore |
| **Провайдер дома** | USB 4G/LTE Multi-WAN на Flint | ❌ нет | **P2** — купить модем + SIM, если частые обрывы |
| **Я.Диск** | 3-2-1 + локальный USB | Я.Диск ✅ · USB Samba/Transmission ✅ · UCI backup ✅ | **P1** — добавить `home_router_backup.sh` в night-pipeline (если ещё не в timer) |
| **Tailscale** | Запасной WireGuard | `wg0 :51820` на Flint + reverse SSH :6223 | ✅ частично. **P2** — документировать fallback: `ssh -p 6223` с VPS |

---

## Чего Gemini не упомянул (но у нас уже есть)

- `empire-router-watchdog` — автопочинка podkop/zapret/torrent каждые 30 мин
- `empire-morning-brief` — ежедневный TG-отчёт
- `empire-weekly-posting-metrics` — KPI постинга 87%
- Audit на Я.Диск: `obsidian (2)/Empire/audit/`

---

## Что реально стоит сделать из отчёта Gemini (минимум)

### P0 — без железа и денег

1. **Uptime Kuma** (или бесплатный UptimeRobot) с ПК/облака — ping `https://gdepar.ru/api/gdepar/health` каждые 5 мин → Telegram. Закрывает SPOF «VPS мёртв».
2. Зафиксировать **fallback-доступ к Flint** в `HOME_NETWORK.md`: reverse SSH → HA → LAN.

### P1 — 1–2 часа

3. Еженедельный **тест restore** (dry-run): `rclone lsf yandex:VPS-backup/` + checklist из `CHECKLIST_AFTER_DISASTER.md`.
4. **Flint UCI** в night-pipeline автоматом (если HA доступен).

### P2 — когда будет бюджет

5. USB 4G модем для Multi-WAN (только если домашний интернет часто падает).
6. Ansible-playbook — обёртка над существующими scripts (не переписывать с нуля).

---

## Диаграмма Gemini vs наша

Gemini нарисовал корректно. Уточнения:

- **VPN на VPS:** VLESS :8443 + Amnezia AWG :39182 (не только «Amnezia»).
- **Backup роутера:** не только Я.Диск — `scripts/infra/home_router_backup.sh` через HA.
- **Watchdog на HA:** у нас watchdog на **VPS**, проверяет Flint **через reverse SSH**; HA — hop для UCI export.

---

**Следующий промпт Gemini:** Промпт 2 (проекты P0/P1) или Промпт 3 (финмодель) — данные уже в `2026-07-15_STATUS_SLICE.md`.
