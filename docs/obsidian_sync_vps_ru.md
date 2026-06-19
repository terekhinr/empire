# Синхронизация Obsidian (Яндекс.Диск) ↔ VPS

**Рабочая схема «всё через VPS»:** `docs/obsidian_vps_workflow_ru.md` (pull vault, push Empire, импорт в бот).

У вас на ПК: `F:\YandexDisk\obsidian (2)\` — vault. Синхронизацию **не меняем**: клиент Яндекс.Диск на Windows как был.

На VPS: **pull** всего `obsidian (2)/` каждые 10 мин (**кроме `Empire/`** — иначе новые файлы агента затираются); **push** `Empire/` после правок агента.

---

## Варианты (кратко)

| Вариант | ПК | VPS | Плюсы | Минусы |
|---------|----|-----|-------|--------|
| **A. rclone → Яндекс.Диск** | Без изменений | `rclone sync` каждые 5–15 мин | Тот же Диск, одна папка `Empire/` | Один раз OAuth в терминале VPS |
| B. rclone → Google Drive | То же | Нужен второй облачный аккаунт | Если vault уже в Google | У вас vault в Яндексе — лишнее |
| C. Офиц. `yandex-disk` CLI | — | Демон Linux | Знакомое имя | Слабая поддержка, конфликты с rclone |
| D. Git (только `Empire/`) | push с ПК | `git pull` на VPS | Контроль версий | Нужна дисциплина, не все умеют |
| E. rsync/scp вручную | — | По запросу | Просто | Не автомат, легко забыть |
| F. Obsidian Sync | Платно | Отдельно от Яндекса | Внутри Obsidian | Другой сервис, не ваш Диск |

**Рекомендация: вариант A (rclone + Яндекс.Диск).**

Почему не ставить «Яндекс.Диск как на Windows» на VPS: полный GUI-клиент на Linux для сервера тяжёлый и дублирует rclone. **rclone** умеет Яндекс.Диск API и тянет только `Empire/`, не весь vault с сотнями `Pasted image`.

Google Drive на VPS имеет смысл только если перенесёте vault в Google — у вас уже Яндекс, **менять не нужно**.

---

## Схема (рекомендуемая)

```text
ПК:  F:\YandexDisk\obsidian (2)\...              ← Obsidian на Windows
          ↕  (клиент Яндекс.Диск)
Облако:  obsidian (2)/...
          ↕  pull каждые 10 мин (rclone)
VPS:   /root/projects/empire/data/obsidian_vault/...
          ↕  push Empire/ после правок агента
Облако → ПК: obsidian (2)/Empire/...
          →  OBSIDIAN_EMPIRE_INCOMING=.../Empire
          →  empire_main импортирует */queue/*.md
```

---

## Что создать на ПК (один раз)

В Obsidian создайте **только** ветку (остальной vault не трогать):

```text
obsidian (2)/Empire/pension/queue/
obsidian (2)/Empire/gdepar/queue/
... (см. дерево на VPS)
```

Посты — в `queue/`, после публикации — в `published/`.

---

## Настройка rclone на VPS (после вашего «да»)

1. Установка: `sudo apt install -y rclone`
2. Конфиг: `rclone config` → remote `yandex` → тип **Yandex Disk** → OAuth (ссылка в браузере, токен в SSH).
3. Проверка:  
   `rclone lsd yandex:` — увидеть `obsidian (2)` или как папка называется в облаке.
4. Тест:  
   `rclone sync yandex:"obsidian (2)/Empire" /root/projects/empire/data/obsidian_vault/Empire -v --dry-run`
5. Таймер: `scripts/obsidian_rclone_sync.sh` + systemd (см. ниже).

В `/etc/empire/empire.env`:

```bash
OBSIDIAN_EMPIRE_INCOMING=/root/projects/empire/data/obsidian_vault/Empire
```

Перезапуск: `sudo systemctl restart empire_main`

---

## Важно

- **Конфликты:** не редактируйте один и тот же файл одновременно на ПК и на VPS в обход Obsidian.
- **Секреты:** токен rclone в `~/.config/rclone/rclone.conf` — не в git.
- Импорт пропускает `published/`, `inbox/`, `_canvas/` — картинки для поста кладите рядом с `.md` в `queue/`.

Чеклист постов: `docs/obsidian_what_you_create.md` · Вариант A/B: `docs/obsidian_practical_guide_ru.md` · **Телефон:** `docs/obsidian_mobile_sync_ru.md`.

---

## Бэкап VPS на тот же Яндекс.Диск

Папка **`VPS-backup/<имя-сервера>/`**: проект Empire (без `venv/`), `/etc/empire`, SQLite, unit-файлы. Ежедневно, хранение 14 дней + `latest/`.

Старт: **`docs/YANDEX_RCLONE_START.md`** · скрипт `scripts/vps_backup_to_yandex.sh`.
