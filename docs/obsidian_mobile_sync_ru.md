# Obsidian на телефоне — полная синхронизация с ПК

**Ваша схема на ПК:** vault = `F:\YandexDisk\obsidian (2)` · синхронизация через **клиент Яндекс.Диск для Windows**.

**Важно про Android:** папки `YandexDisk\obsidian (2)` **на телефоне нет** — мобильное приложение Яндекс.Диска **не зеркалирует** файлы в проводник, как на Windows. Это нормально, не ваша ошибка.

**Рабочая схема на телефоне:** локальная папка в **Документах** + плагин **Remotely Save** (WebDAV → тот же каталог `obsidian (2)` в облаке).

Связанные гайды:
- Установка с нуля на ПК: `docs/obsidian_install_zero_ru.md`
- VPS ↔ `Empire/`: `docs/obsidian_sync_vps_ru.md`, `docs/obsidian_vps_workflow_ru.md`
- Задачи TickTick → Obsidian: `docs/obsidian_tasks_ticktick_ru.md`

---

## 1. Как это связано с ПК

```text
ПК:  Obsidian → F:\YandexDisk\obsidian (2)\  →  клиент Яндекс.Диск  →  облако
                                                                      ↕
Телефон:  Obsidian → Документы/obsidian-phone\  →  Remotely Save WebDAV  →  облако
                                                         (папка obsidian (2))
```

| Папка в vault | На телефоне | На VPS |
|---------------|-------------|--------|
| `Empire/` | ✅ через sync | ✅ rclone |
| `Life/` | ✅ | ❌ |
| `База знаний/`, `Входящие/` | ✅ | ❌ |

На ПК **ничего менять не нужно** — оставляете `F:\YandexDisk\obsidian (2)` как есть.

---

## 2. Android — пошагово (рабочая схема)

### Шаг 0 — Пароль WebDAV (один раз, на телефоне или ПК)

1. Откройте [Пароли приложений Яндекс ID](https://id.yandex.ru/security/app-passwords).
2. **Создать** → тип **Файлы WebDAV** (или WebDAV).
3. Имя: `Obsidian phone`.
4. Скопируйте пароль — показывается **один раз**.

Обычный пароль от почты **не подойдёт**.

### Шаг 1 — Obsidian: локальная папка vault

1. Установите [Obsidian](https://play.google.com/store/apps/details?id=md.obsidian) из Google Play.
2. Первый запуск → **Create new vault** (Создать хранилище).
3. Имя vault: `obsidian-phone` (любое).
4. Когда спросит **где хранить** — выберите **Device storage** / **Хранилище устройства** (не «App storage»).
5. В проводнике выберите путь:

```text
Внутренняя память  →  Documents  →  (создать папку) obsidian-phone
```

**Как это выглядит в меню (зависит от прошивки):**

| Вариант в проводнике | Куда идти |
|----------------------|-----------|
| Samsung «Мои файлы» | **Внутреннее хранилище** → **Documents** |
| Stock Android | **Internal storage** → **Documents** |
| Xiaomi / др. | **Хранилище телефона** → **Документы** |

**Не ищите:** `YandexDisk`, `Яндекс.Диск`, `obsidian (2)` — их **нет** в файловой системе телефона.

Полный путь (для справки, вручную не вводить):

```text
/storage/emulated/0/Documents/obsidian-phone/
```

### Шаг 2 — Синхронизация с облаком (выберите один вариант)

#### Вариант A — **Yandex Disk Sync** (рекомендуется, если WebDAV даёт 429)

Плагин в Community plugins: **Yandex Disk Sync** (автор Nikolay-Eltsov).  
Использует **OAuth API Яндекса**, не WebDAV — обходит ошибку `429 Too Many Requests`.

1. **Settings → Community plugins → Browse** → **Yandex Disk Sync** → Install → Enable.
2. **Войти через Яндекс** → код из браузера → Подтвердить.
3. **Remote folder path:** `obsidian (2)` (как папка на Диске).
4. Первый раз: команда **Pull all** / «Скачать с облака» (не Push).
5. **Exclude patterns** (чтобы не тянуть мусор):  
   `**/.trash/**`, `**/node_modules/**`, `**/*.canvas` (по желанию).

#### Вариант B — Remotely Save + WebDAV (часто ломается на Яндексе)

Если всё же Remotely Save — настройки **обязательно**:

| Параметр | Значение |
|----------|----------|
| Server | `https://webdav.yandex.ru` |
| Password | пароль приложения **WebDAV** (не почты) |
| Remote base directory | `obsidian (2)` |
| **Concurrency** | **1** |
| **Sync on save** | **Off** |
| **Schedule auto run** | **Off** |
| **Sync config dir** | **Off** (иначе тянет `.obsidian` — тысячи файлов → 429) |
| Depth header | попробуйте **supports depth='infinity'**; если 429 — **only depth='1'** |

Синхронизация **только вручную**. После ошибки 429 — подождать **30–60 мин**, не жать Sync подряд.

**Ошибка `Invalid response: 429 Too Many Requests`** = лимит Яндекса. Решение: вариант A, или ночью первая Pull при Concurrency=1 и выключенном config dir.

---

### Шаг 3 — (если используете Remotely Save) первая синхронизация

1. **Pull all** / Download (Yandex Disk Sync) **или** Remotely Save → Sync → download.
2. Wi‑Fi, первый раз 10–30 мин.

Проверка — откройте на телефоне:

- `Empire/000 — СЕГОДНЯ.md`
- `Empire/000 — ПРОГРЕСС.md`
- `Life/tasks/inbox.md`

### Шаг 4 — Автосинк (рекомендуется)

В настройках Remotely Save:

- **Run once on startup** — включить (sync через 1–5 сек после открытия).
- **Advanced → Concurrency** — поставить **1** (меньше ошибок 429 от Яндекса).
- Интервал полной синхронизации — 15–30 мин или вручную перед/после правок.

### Шаг 5 — Плагин Tasks

1. **Community plugins** → **Tasks** → Install → Enable.
2. Закладка: `Life/tasks/dashboard.md`.

Формат:

```markdown
- [ ] Купить молоко 📅 2026-06-15 #дом
```

### Шаг 6 — Что не нужно на телефоне

| На ПК | На телефоне |
|-------|-------------|
| Geminese / `gemini` CLI | Не нужно |
| Открывать папку Яндекс.Диска как vault | **Не работает** на Android |
| Приложение Яндекс.Диск для sync vault | Только для просмотра файлов в облаке; sync делает Remotely Save |

---

## 3. iOS (iPhone / iPad)

Та же схема, что Android:

1. Obsidian → **Create new vault** → папка в **On My iPhone** → `Documents/obsidian-phone` (через «Файлы»).
2. **Remotely Save** → WebDAV → `https://webdav.yandex.ru` → remote base **`obsidian (2)`**.
3. Первый раз — **download** с облака.

Папки `YandexDisk` в «Файлах» на iOS тоже обычно **нет** как локального vault.

---

## 4. Синхронизация ПК ↔ телефон (ритм)

| Сделали | Действие |
|---------|----------|
| Правка на **ПК** | Дождаться галочки Яндекс.Диска в трее Windows → на телефоне **Remotely Save → Sync** |
| Правка на **телефоне** | **Remotely Save → Sync** → подождать → на ПК дождаться синка Яндекс.Диска |
| Агент на VPS обновил `Empire/` | ПК подхватит с Диска → на телефоне **Sync** |

**Не правите один и тот же `.md` одновременно** на ПК и телефоне.

---

## 5. Правила Empire / Life / VPS

- `Empire/*/queue/` → уходит в Telegram-бот; личные задачи только в `Life/tasks/`.
- VPS пушит только `Empire/`; `Life/` — только ПК ↔ облако ↔ телефон.

---

## 6. Напоминания

Obsidian на телефоне **не пинает** в точное время → срочное с временем дублируйте в **Tasks.org** (`docs/obsidian_tasks_ticktick_ru.md`).

---

## 7. Частые проблемы

| Симптом | Решение |
|---------|---------|
| **Нет папки YandexDisk в проводнике** | Ожидаемо. Vault = `Documents/obsidian-phone` + Remotely Save |
| WebDAV «не подключается» | Пароль приложения WebDAV, не пароль почты; проверить username с/без `@domain` |
| Ошибка **429 / Invalid response: too many requests** | Яндекс WebDAV. **Перейти на плагин Yandex Disk Sync** (OAuth). Или: Concurrency=1, Sync config dir=Off, только ручной sync, пауза 1 ч |
| На телефоне пустой vault | Первый sync — **download**, не upload |
| На телефоне нет `000 — ПРОГРЕСС` | Remote base directory = `obsidian (2)`; на ПК файл есть в `F:\YandexDisk\...`? |
| Две копии одного файла | Конфликт; разобрать на ПК в `F:\YandexDisk\obsidian (2)\` |
| ПК не видит правки с телефона | Sync на телефоне → подождать → галочка Яндекс.Диска на Windows |

---

## 8. Чеклист «телефон настроен»

- [ ] Vault на телефоне: **Documents/obsidian-phone** (не YandexDisk)
- [ ] Remotely Save: WebDAV, base directory **`obsidian (2)`**
- [ ] Первая синхронизация: download с облака прошла
- [ ] Видны `Empire/000 — СЕГОДНЯ` и `Life/tasks/inbox`
- [ ] Tasks включён
- [ ] После правок на телефоне — жму Sync перед закрытием Obsidian

---

*Обновлено: 2026-06-11. ПК: `F:\YandexDisk\obsidian (2)` · Телефон: `Documents/obsidian-phone` + Remotely Save WebDAV.*
