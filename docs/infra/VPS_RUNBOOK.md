# VPS Runbook — Empire с нуля

Цель: поднять **193.233.232.48** (или новый VPS) из бэкапа на Яндекс.Диске за **1–3 часа**.

## Предварительно

- Ubuntu/Debian VPS, root по SSH
- На **старом** VPS или с ПК: доступ к `yandex:` через rclone **или** скачать `VPS-backup/<host>/latest/` через веб Я.Диска

## 1. Базовая система

```bash
apt update && apt install -y git python3 python3-venv nginx certbot \
  python3-certbot-nginx sqlite3 rclone curl tmux
```

## 2. rclone + Яндекс

```bash
# С ПК: скопировать /root/.config/rclone/rclone.conf с старого VPS
# или заново:
cd /root/projects/empire   # после шага 3
sudo bash scripts/rclone_setup_yandex_webdav.sh
sudo nano /etc/empire/rclone.env
```

Проверка: `rclone lsd yandex:VPS-backup/`

## 3. Восстановление из бэкапа

```bash
git clone https://github.com/YOUR/empire.git /root/projects/empire   # если нет git — только rclone
cd /root/projects/empire
sudo bash scripts/infra/vps_restore_from_yandex.sh latest
```

Скрипт:
- скачает `yandex:VPS-backup/<hostname>/latest/empire` → `/root/projects/empire`
- распакует `etc-empire.tar.gz` → `/etc/empire`
- скопирует systemd units
- восстановит SQLite из `sqlite-backups/`

## 4. Python окружение

```bash
cd /root/projects/empire
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## 5. systemd

```bash
sudo cp deploy/empire_*.service /etc/systemd/system/   # или из бэкапа systemd/
sudo cp deploy/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now empire_main empire_worker empire_webapp \
  empire_gdepar empire_dashboard obsidian-rclone-sync.timer
```

Полный список: `deploy/README.md`, `scripts/deploy_empire_infra.sh`.

## 6. Nginx + TLS

```bash
sudo cp deploy/nginx/empire_hub /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/empire_hub /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d neverretire.ru -d gdepar.ru -d hub.neverretire.ru
```

**Важно:** сертификаты Let's Encrypt **не** в ежедневном бэкапе — после restore нужен `certbot` заново (или ручной копипаст `/etc/letsencrypt` со старого VPS).

## 7. Проверки

```bash
systemctl status empire_main empire_gdepar --no-pager
curl -s http://127.0.0.1:8001/api/gdepar/health
curl -sI https://gdepar.ru/ | head -3
curl -s http://127.0.0.1:8789/ | head -1   # если bootstrap запущен
```

## 8. Tailscale (опционально)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
# В админке Tailscale: empire-vps-ts → 100.84.19.35
```

## 9. Docker Amnezia (если был)

```bash
docker ps -a | grep amnezia
# Образ и volume — отдельно не в code backup; конфиг клиентов в Amnezia app
```

## 10. Cron / tmux

```bash
crontab -l                    # сверить с docs/infra/BACKUP_AND_RESTORE.md
tmux ls                       # empire-backups, flint2-watch — по необходимости
systemctl list-timers | grep empire
```

## Логи

```bash
journalctl -u empire_main -f
tail -f /var/log/empire/night-pipeline-latest.log
```

## Если бэкапа нет

1. Клонировать git (если репозиторий актуален)
2. `/etc/empire/*.env` — восстановить вручную из KeePass / Я.Диска / старого VPS
3. `docs/EMPIRE_PIPELINE_CHECKLIST.md`, `deploy/README.md`
