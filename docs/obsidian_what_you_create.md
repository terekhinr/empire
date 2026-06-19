# Вариант A (Obsidian): что создать вам — чеклист

Код на VPS уже умеет импорт, `scheduled`, черновик в Telegram и `/obsidian`. **Без ваших папок и env это не запустится.**

## 1. В Obsidian (vault)

Создайте структуру (можно копировать из `templates/obsidian_vault_README.md`):

```text
Empire/
  pension/queue/     ← готовые посты «На пенсию…»
  garden/queue/
  gdepar/queue/
  stern/queue/
  lenin/queue/
  pension/published/ ← сюда переносите после выхода поста
```

В каждом посте в **`queue/`** — frontmatter:

```yaml
---
id: "2026-05-20-moi-zagolovok"
persona: pension
title: "Заголовок для Telegram"
scheduled: "2026-05-20 10:00"
status: ready
image: foto.jpg
---
```

- `status: ready` — попадёт в очередь; `draft` — импорт есть, в бот **не** уйдёт.
- `image:` — файл **рядом** с `.md` (имя из frontmatter).
- Время `scheduled` — **МСК**, формат `ГГГГ-ММ-ДД ЧЧ:ММ`.

Шаблон заметки: `templates/obsidian_empire_post.md`.

## 2. Доставка vault на VPS

**Рекомендуется:** Яндекс.Диск на ПК как сейчас + **rclone** на VPS → `docs/obsidian_sync_vps_ru.md`

На VPS дерево уже создано: `/root/projects/empire/data/obsidian_vault/Empire/`

В `/etc/empire/empire.env`:

```bash
OBSIDIAN_EMPIRE_INCOMING=/root/projects/empire/data/obsidian_vault/Empire
```

| Способ | Когда |
|--------|--------|
| **rclone + Яндекс.Диск** | Основной, ПК не меняется |
| Git только `Empire/` | Если не хотите OAuth на VPS |
| Симлинк / rsync | Ручные тесты |

На ПК создайте **ту же** структуру: `YandexDisk\obsidian (2)\Empire\...`

## 3. На VPS (один раз + после деплоя)

```bash
cd /root/projects/empire
# в environment empire_main:
export OBSIDIAN_EMPIRE_INCOMING=/path/to/queue
export ADMIN_ID=ваш_telegram_id
sudo systemctl restart empire_main
```

Проверка:

```bash
./venv/bin/python scripts/import_obsidian_queue.py
./venv/bin/python -m pytest tests/test_obsidian_import.py tests/test_obsidian_dispatch.py -q
```

В Telegram: `/obsidian list`, тест — `/obsidian now <id>`.

## 4. Telegram / каналы (уже должны быть в Empire)

| Переменная / настройка | Зачем |
|------------------------|--------|
| `ADMIN_ID` | Кому приходят черновики и напоминания |
| Chat ID каналов (pension, gdepar, …) | Куда «Опубликовать» — см. `main.py` / env проекта |

Без `ADMIN_ID` вариант A молчит (очередь крутится, сообщений нет).

## 5. Опционально

- **Metrika:** `YANDEX_METRIKA_ID` + цели — `docs/metrika_goals_setup.md` (когда создадите счётчик).
- Несколько каналов Obsidian: меняйте `OBSIDIAN_EMPIRE_INCOMING` на другой `queue` или держите отдельные симлинки + ручной import перед сменой канала.
- Повторный пост с тем же `id` после публикации: новый `id` в frontmatter или очистите `data/obsidian_dispatch_state.json` (осторожно — возможен дубль).

## 6. Вариант B (расписание) — без Obsidian

Редактируете `content_config.json` на VPS — слоты 08:00, 11:00 и т.д. Obsidian для этого **не нужен**.

Полный гайд: `docs/obsidian_practical_guide_ru.md`.  
**Старт rclone + бэкап VPS:** `docs/YANDEX_RCLONE_START.md`  
**Рост ВК/Дзен/TG (чеклисты):** скопировать `templates/obsidian_growth_rf_2026.md` → `Empire/_scenarios/growth-rf-2026.md`
