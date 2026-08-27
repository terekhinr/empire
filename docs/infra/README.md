# Empire — инфраструктура: документация и восстановление

**Назначение:** один вход для всего, что не «контент gdepar», а **сеть, VPS, бэкапы, восстановление**.

| Документ | Когда читать |
|----------|--------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Схема: что где крутится, IP, порты |
| [HOME_NETWORK.md](HOME_NETWORK.md) | Flint 2, Keenetic, Wi‑Fi, podkop, Amnezia, USB |
| [VPS_RUNBOOK.md](VPS_RUNBOOK.md) | Поднять Empire с нуля на VPS |
| [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md) | Яндекс.Диск, rclone, что куда, как откатить |
| [CHECKLIST_AFTER_DISASTER.md](CHECKLIST_AFTER_DISASTER.md) | Пошагово после поломки / нового VPS |
| [../audit/2026-07-15_FULL_INFRA_AUDIT.md](../audit/2026-07-15_FULL_INFRA_AUDIT.md) | Полный аудит + приоритеты P0/P1/P2 |
| [../audit/GEMINI_AUDIT_PROMPTS.md](../audit/GEMINI_AUDIT_PROMPTS.md) | Промпты для повторного аудита в Gemini |
| [SELF_HEAL.md](SELF_HEAL.md) | Самопочинка + PWA на Flint + Tailscale/WG |
| [../scripts/flint2/empire-flint-watchdog/README.md](../../scripts/flint2/empire-flint-watchdog/README.md) | Сторож + PWA на OpenWrt |

**Мониторинг (systemd):**

| Timer | Назначение |
|-------|------------|
| `empire-service-healer` | каждые 5 мин — **весь стек**: сайты, софт, HA, роутер, Docker + автопочинка + TG |
| `empire-router-watchdog` | каждые 30 мин — podkop/zapret/torrent на Flint + автопочинка |
| `empire-diagnostics-watchdog` | каждые 2 ч — таймеры, аудит, бэкапы |
| `empire-morning-brief` | 07:05 MSK — короткий TG: VPS + роутер + постинг |
| `empire-daily-audit` | 07:00 MSK — полный аудит |
| `empire-weekly-posting-metrics` | вс 08:30 MSK — KPI постинга → `data/empire_weekly_kpi.json` |

Деплой: `sudo bash scripts/deploy_empire_monitoring.sh`

**Яндекс.Диск:** `obsidian (2)/Empire/audit/` — `sudo bash scripts/export_audit_to_yandex.sh` (авто 07:15 МСК)

**На Яндекс.Диске (rclone `yandex:`):**

```
VPS-backup/<hostname>/latest/
  empire/              # код + docs/infra/
  etc-empire.tar.gz    # /etc/empire (секреты)
  systemd/             # empire*.service + timers
  sqlite-backups/      # empire.db снимки
  infra/               # снимок домашней сети + flint2 (если доступен)
```

**Быстрый бэкап вручную:**

```bash
cd /root/projects/empire
sudo bash scripts/infra/infra_backup_bundle.sh    # собрать infra + роутер
sudo bash scripts/vps_backup_to_yandex.sh         # на Я.Диск
```

**Быстрое восстановление VPS:**

```bash
sudo bash scripts/infra/vps_restore_from_yandex.sh latest
```

Подробности: [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md).
