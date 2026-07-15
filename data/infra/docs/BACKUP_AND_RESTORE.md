# Бэкап и восстановление — Яндекс.Диск + rclone

## Обзор

| Что | Куда | Как часто |
|-----|------|-----------|
| Код Empire + `docs/infra/` | `yandex:VPS-backup/<host>/latest/empire/` | Ночной pipeline ~01:00 MSK |
| `/etc/empire/` | `etc-empire.tar.gz` | То же |
| SQLite | `sqlite-backups/` | Ежедневно 03:15 UTC + в pipeline |
| systemd units | `systemd/` | То же |
| Домашняя сеть (Flint UCI) | `infra/home-router/` | При `infra_backup_bundle.sh` |
| Obsidian посты | `yandex:obsidian (2)/Empire/` | Каждые 10 мин (pull) |
| HA | Google Drive (addon на TOX1) | По расписанию HA |
| Крупные файлы (>80MB) | `vps_large_files_to_cloud.sh` | Ночью |

## Настройка rclone (один раз)

Полный гайд: **`docs/YANDEX_RCLONE_START.md`**

```bash
cd /root/projects/empire
sudo bash scripts/install_rclone_empire.sh
sudo nano /etc/empire/rclone.env      # YANDEX_DISK_USER + пароль приложения
sudo bash scripts/rclone_setup_yandex_webdav.sh
```

Проверка:

```bash
rclone lsd yandex:
rclone lsd yandex:VPS-backup/$(hostname -s)/
```

## Ручной бэкап «всё сейчас»

```bash
cd /root/projects/empire

# 1) Снимок домашней сети + infra-доки
sudo bash scripts/infra/infra_backup_bundle.sh

# 2) На Я.Диск
sudo bash scripts/vps_backup_to_yandex.sh

# 3) SQLite отдельно (если нужно)
sudo bash scripts/backup_empire_db.sh
```

Ожидаемое время: 10–40 мин (без venv/media).

## Что **не** попадает в ежедневный бэкап

| Путь | Как сохранить |
|------|---------------|
| `venv/` | `pip install -r requirements.txt` после restore |
| `media/`, `data/gdepar/`, `data/audio/` | `scripts/vps_large_files_to_cloud.sh` |
| `data/obsidian_vault/` | Obsidian rclone sync |
| `/etc/nginx/`, `/etc/letsencrypt/` | Вручную или `scripts/infra/infra_backup_bundle.sh` (nginx из repo) |
| `/root/.config/rclone/rclone.conf` | В `infra/rclone.conf.backup` (bundle) |
| Образ TOX1 eMMC | `TOX1/parts/` на Я.Диске |
| Flint live config | `home_router_backup.sh` |

## Восстановление VPS

```bash
# Список бэкапов
rclone lsd yandex:VPS-backup/$(hostname -s)/

# Последний
sudo bash /root/projects/empire/scripts/infra/vps_restore_from_yandex.sh latest

# Конкретная дата
sudo bash /root/projects/empire/scripts/infra/vps_restore_from_yandex.sh 2026-07-15
```

После restore: **VPS_RUNBOOK.md** §4–7 (venv, systemd, certbot).

## Восстановление домашней сети

1. Скачать с Я.Диска: `VPS-backup/<host>/latest/infra/home-router/`
2. Следовать **HOME_NETWORK.md** § «Восстановление Flint»
3. Keenetic-снимок (если Flint недоступен): `scripts/flint2/keenetic-export.json`

## Расписание (systemd)

```bash
systemctl list-timers | grep -E 'empire|obsidian|backup'
journalctl -u empire-night-pipeline.service -n 50
journalctl -u empire-vps-backup-yandex.service -n 50
```

Ночной pipeline: `scripts/empire_night_pipeline.sh` (~22:00 UTC).

Если бэкапы зависли:

```bash
sudo bash scripts/empire_unblock_backups.sh
```

## Хранение

- Дневные папки `VPS-backup/<host>/YYYY-MM-DD/` — **14 дней**
- `latest/` — всегда последний успешный

## Безопасность

- `etc-empire.tar.gz` и `rclone.conf.backup` содержат **секреты** — Я.Диск под вашим аккаунтом, не публичные ссылки
- Не коммитить `.env`, `client.env`, `rclone.conf` в git

## Быстрая проверка «бэкап жив»

```bash
rclone size yandex:VPS-backup/$(hostname -s)/latest/
rclone ls yandex:VPS-backup/$(hostname -s)/latest/ | head -20
test -f /var/log/empire/night-pipeline-latest.log && tail -5 /var/log/empire/night-pipeline-latest.log
```
