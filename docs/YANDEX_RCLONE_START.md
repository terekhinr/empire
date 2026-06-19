# Старт: rclone + Яндекс.Диск (Obsidian + бэкап VPS)

## 1. Пароль приложения (5 мин, на ПК)

1. Откройте [Пароли приложений Яндекс ID](https://id.yandex.ru/security/app-passwords).
2. Создайте пароль (название: `VPS rclone`).
3. Скопируйте пароль — показывается один раз.

## 2. На VPS (SSH)

```bash
cd /root/projects/empire
sudo bash scripts/install_rclone_empire.sh
sudo nano /etc/empire/rclone.env   # логин + пароль приложения
sudo bash scripts/rclone_setup_yandex_webdav.sh
sudo bash scripts/install_rclone_empire.sh
sudo systemctl restart empire_main
```

Проверка Obsidian:

```bash
sudo bash scripts/obsidian_rclone_sync.sh
ls -la data/obsidian_vault/Empire/pension/queue/
```

Проверка бэкапа (первый раз ~10–30 мин без venv):

```bash
sudo bash scripts/vps_backup_to_yandex.sh
rclone lsd yandex:VPS-backup/
```

## 3. На ПК (Obsidian)

Создайте зеркало структуры (как на VPS):

`YandexDisk\obsidian (2)\Empire\pension\queue\` и т.д.

Яндекс.Диск на Windows синхронизирует в облако → VPS подтягивает `Empire/`.

## Что куда на Диске

| Папка на Яндекс.Диске | Направление | Содержимое |
|----------------------|-------------|------------|
| `obsidian (2)/Empire/` | облако → VPS | Ваши посты Obsidian |
| `VPS-backup/<имя-сервера>/` | VPS → облако | Код Empire, `.env`, БД, systemd |

## Бэкап — что именно сохраняется

Не весь образ диска VPS, а **восстановимый минимум**:

- `/root/projects/empire` **без** `venv/` (5+ ГБ — ставится заново: `python -m venv venv && pip install -r requirements.txt`)
- `/etc/empire/` (секреты, `rclone.env`)
- `empire.db`, `analytics.db`, `sales.db` (снимки в `sqlite-backups/`)
- unit-файлы `empire*.service`

Расписание: ежедневно ~03:45, хранение дневных папок **14 дней** + папка `latest/`.

## Команды

```bash
systemctl status obsidian-rclone-sync.timer
systemctl status empire-vps-backup-yandex.timer
journalctl -u obsidian-rclone-sync.service -n 30
journalctl -u empire-vps-backup-yandex.service -n 30
```

Полный гайд Obsidian: `docs/obsidian_sync_vps_ru.md`.
