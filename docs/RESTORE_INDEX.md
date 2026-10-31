# Empire — восстановление и документация (оглавление)

**Начни здесь**, если VPS/роутер/бот сломались или нужно поднять всё с нуля.

Полный срез схем, аудита и промптов для другого ИИ (31.10.2026): [handoff/2026-10-31/README.md](handoff/2026-10-31/README.md).

---

## Быстрые ссылки

| Ситуация | Документ | Команда |
|----------|----------|---------|
| Упал VPS, нужен код и секреты | [VPS_RESTORE_RUNBOOK.md](VPS_RESTORE_RUNBOOK.md) | `sudo bash scripts/vps_restore_from_yandex.sh latest` |
| Сломался Flint / нет YouTube/TG/Samba | [HOME_NETWORK_RUNBOOK.md](HOME_NETWORK_RUNBOOK.md) | см. раздел «Восстановление роутера» |
| Не понимаю, что и куда бэкапится | [BACKUP_AND_DR.md](BACKUP_AND_DR.md) | `sudo bash scripts/vps_backup_to_yandex.sh` |
| rclone / Яндекс не настроен | [YANDEX_RCLONE_START.md](YANDEX_RCLONE_START.md) | `sudo bash scripts/rclone_setup_yandex_webdav.sh` |
| Home Assistant | [HA_GOOGLE_DRIVE_BACKUP.md](HA_GOOGLE_DRIVE_BACKUP.md) | GDrive addon на HA |
| Cursor → VPS | [cursor_vps_ssh_ru.md](cursor_vps_ssh_ru.md) | Tailscale + SSH key |
| Flint миграция (детали) | [FLINT2_SETUP.md](FLINT2_SETUP.md) | bootstrap `:8789` |
| YouTube на Flint (VPS и без) | [FLINT2_YOUTUBE_DUAL.md](FLINT2_YOUTUBE_DUAL.md) | `20-mode-vps.sh` / `21-mode-novps.sh` |

---

## Где лежит бэкап на Яндекс.Диске

```
YandexDisk/
├── VPS-backup/
│   └── <hostname>/          # например moderate-amethys
│       ├── latest/          # ← последний снимок (для restore)
│       │   ├── empire/      # код проекта (без venv)
│       │   ├── etc-empire.tar.gz
│       │   ├── sqlite-backups/
│       │   ├── systemd/
│       │   ├── nginx/
│       │   ├── infra/       # домашняя сеть + manifest
│       │   └── backup-manifest.json
│       └── YYYY-MM-DD/      # дневные снимки (14 дней)
├── obsidian (2)/Empire/     # Obsidian ↔ VPS (отдельный sync)
└── Empire-large/            # тяжёлые файлы (night pipeline)
```

---

## Расписание (VPS)

| Задача | Когда (MSK) | Скрипт / unit |
|--------|-------------|---------------|
| SQLite снимки | ~06:15 | cron → `backup_empire_db.sh` |
| Полный бэкап → Яндекс | ~01:00 (night pipeline) | `empire_night_pipeline.sh` → `vps_backup_to_yandex.sh` |
| Obsidian pull | каждые 10 мин | `obsidian-rclone-sync.timer` |
| Домашняя инфра в бэкап | вместе с VPS | `home_infra_backup.sh` |

Ручной бэкап всего:

```bash
cd /root/projects/empire
sudo bash scripts/home_infra_backup.sh
sudo bash scripts/vps_backup_to_yandex.sh
```

---

## Схема (одним взглядом)

```
Интернет
   │
   ├── Flint 2 (192.168.1.1) ── LAN ── HA, ПК, TV, камеры
   │      podkop → VLESS Empire :8443 (YouTube, TG, Gemini)
   │      awg0 → Amnezia :39182 (AI — когда туннель живой)
   │      USB → Samba \\192.168.1.1\download, Transmission
   │
   └── Empire VPS (193.233.232.48 / Tailscale 100.84.19.35)
          empire_main (TG бот), gdepar, webapp, nginx
          bootstrap :8789, Amnezia docker, VLESS :8443
          бэкап → Яндекс VPS-backup/
```

---

## Секреты (не в git)

| Файл | Назначение |
|------|------------|
| `/etc/empire/*.env` | прод-секреты ботов и сервисов |
| `/root/.config/rclone/rclone.conf` | Яндекс + GDrive |
| `/root/projects/empire/.env` | локальные ключи (если есть) |
| `scripts/flint2/amnezia-client.env` | ключи Amnezia (только на VPS, не коммитить) |
| `/root/.keenetic-admin.env`, `/root/.flint-admin.env` | пароли роутеров |

В бэкап попадает `/etc/empire/` (tar) и rclone.conf (отдельный tar в infra).

---

## Чеклист «всё живо»

**Дом:**
- [ ] `ping 192.168.1.1`
- [ ] YouTube на TV/телефоне
- [ ] Telegram на ПК без Amnezia
- [ ] `\\192.168.1.1\download` открывается
- [ ] `awg show awg0` — handshake < 2 мин (если нужен AI через Amnezia)

**VPS:**
- [ ] `systemctl is-active empire_main empire_gdepar nginx`
- [ ] `curl -s http://127.0.0.1:8001/api/gdepar/health`
- [ ] `rclone lsd yandex:VPS-backup/$(hostname -s)/latest`

Обновлено: 2026-07-15
