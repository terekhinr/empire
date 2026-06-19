# Obsidian через VPS — рабочая схема

Vault на ПК: `F:\YandexDisk\obsidian (2)\`  
На VPS: `/root/projects/empire/data/obsidian_vault/`  
Empire для бота: `.../obsidian_vault/Empire/` → `OBSIDIAN_EMPIRE_INCOMING`

## Поток

```text
ПК (Obsidian)  →  Яндекс.Диск  →  pull каждые 10 мин  →  VPS
                                                              ↓
                                                    агент правит .md
                                                              ↓
ПК (Obsidian)  ←  Яндекс.Диск  ←  push Empire/  ←  obsidian_vps_publish.sh
```

| Действие | Кто | Команда / автомат |
|----------|-----|-------------------|
| Пишете заметки | Вы на ПК | Obsidian + клиент Яндекс.Диск |
| Забрать vault на VPS | Таймер | `obsidian-rclone-sync.timer` → pull |
| Правки структуры, queue | Агент на VPS | файлы в `data/obsidian_vault/` |
| Отдать правки на ПК | После правок агента | `sudo bash scripts/obsidian_vps_publish.sh` |
| Импорт в Telegram | Бот | `check_obsidian_queue` каждую минуту |

## Команды на VPS

```bash
cd /root/projects/empire

# Забрать весь vault с Диска (Life, Empire, Main…)
sudo bash scripts/obsidian_rclone_pull.sh

# Отдать только Empire/ обратно на Диск (ПК увидит через sync)
sudo bash scripts/obsidian_rclone_push.sh

# Импорт queue + push (после сессии с агентом)
sudo bash scripts/obsidian_vps_publish.sh
```

## Правила, чтобы не сломать vault

1. **Не править один файл** одновременно на ПК и пока агент пушит с VPS.
2. **Pull** перезаписывает VPS версией из облака (кроме `published/` — не тянем).
3. **Push** перезаписывает **только `Empire/`** в облаке — `Life/` и личное на VPS read-only после pull.
4. Посты: `Empire/*/queue/` + `status: ready` → approve в боте.

## Env (`/etc/empire/rclone.env`)

```bash
RCLONE_VAULT_REMOTE_PATH="obsidian (2)"
OBSIDIAN_VAULT_ROOT=/root/projects/empire/data/obsidian_vault
RCLONE_REMOTE_PATH="obsidian (2)/Empire"
```

## Env (`/etc/empire/empire.env`)

```bash
OBSIDIAN_EMPIRE_INCOMING=/root/projects/empire/data/obsidian_vault/Empire
```

Подробнее про rclone: `docs/obsidian_sync_vps_ru.md`

Cursor Remote SSH (ключ, keepalive, после обрыва): `docs/cursor_vps_ssh_ru.md`
