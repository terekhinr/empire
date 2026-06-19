# Вечерний сетап: Geminese + TickTick + голос (только Яндекс.Диск)

**~2 часа.** Репозиторий Empire на ПК **не нужен**. VPS **не трогаем**.

---

## Как у вас устроено (и так остаётся)

```text
ПК + телефон                    Яндекс.Диск (облако)              VPS
─────────────────              ─────────────────────             ─────
Obsidian открывает      ↔      obsidian (2)/              ↔      только
F:\YandexDisk\                  Empire/  → rclone                  Empire/
  obsidian (2)\                 Life/    (личное,                  для ботов
                                на VPS не едет)
```

| Папка в vault | Кто использует |
|---------------|----------------|
| `Empire/` | Вы, Obsidian, Geminese → sync → Telegram |
| `Life/` | Вы: задачи, голос (TickTick, диктофон) |
| `.obsidian/plugins/` | Плагины Obsidian на ПК |

**Искать `main.py` на C: не нужно** — это код ботов на сервере, не ваши заметки.

**Одна переменная на вечер:**

```powershell
$VAULT = "F:\YandexDisk\obsidian (2)"
```

---

## Опционально: мини-набор скриптов в vault (5 мин)

Чтобы не клонировать Empire, один раз скопируйте с VPS (Cursor) в vault:

```text
templates/obsidian_life_kit/*.py  →  F:\YandexDisk\obsidian (2)\Life\tools\
```

Geminese (3 файла) с VPS:

```text
templates/obsidian_plugins/geminese/  →  F:\YandexDisk\obsidian (2)\.obsidian\plugins\geminese\
```

Без VPS: плагин Geminese — [GitHub Momoyu404/geminese](https://github.com/Momoyu404/geminese) (папка релиза или BRAT в Obsidian).

---

## Блок 0 — Папки Life (10 мин)

В Total Commander или проводнике под `$VAULT` создайте:

```text
Life/
  README.md
  tasks/
    inbox.md
    dashboard.md
    _import/
  voice/
    raw/
    transcribed/
    processed/
  inbox/
  tools/          ← сюда .py, если копировали
```

**`Life/tasks/inbox.md`:**

```markdown
# Inbox

## Без срока

```

**`Life/tasks/dashboard.md`:**

````markdown
# Задачи

## Просрочено
```tasks
not done
due before today
sort by due
```

## Сегодня
```tasks
not done
due today
```

## Следующие 7 дней
```tasks
not done
due after today
due before in 7 days
sort by due
```
````

Obsidian: **Settings → Community plugins → Tasks** → включить. Закладка на `dashboard.md`.

Дождитесь синка Яндекс.Диска (иконка «галочка»).

---

## Блок 1 — Geminese (40 мин)

### 1.1 Gemini CLI (в Windows, не в Obsidian)

PowerShell:

```powershell
node -v
npm install -g @google/gemini-cli
gemini
```

Логин Google в браузере. Проверка:

```powershell
where.exe gemini
gemini -p "Ответь одним словом: ок"
```

Путь для **Geminese** — из `Get-Content "$env:APPDATA\npm\gemini.cmd"` (0.43+ обычно):

```text
C:\Users\Destroy\AppData\Roaming\npm\node_modules\@google\gemini-cli\bundle\gemini.js
```

### 1.2 Три файла плагина в vault

Скопировать в:

```text
F:\YandexDisk\obsidian (2)\.obsidian\plugins\geminese\
  main.js
  manifest.json
  styles.css
```

Источник: VPS `templates/obsidian_plugins/geminese/` **или** релиз GitHub.

### 1.3 Obsidian

1. Закрыть Obsidian полностью → открыть vault `obsidian (2)`.
2. **Settings → Community plugins → Reload** → включить **Geminese**.
3. **Settings → Geminese:** при ENOENT — CLI path = **.js из gemini.cmd** (часто `bundle\gemini.js`); **Plan** mode.
4. Первое сообщение в чате — правила из файла на VPS `templates/geminese_empire_system_prompt.txt` (скопировать текст в чат; файл можно положить в `Life/tools/` в vault).

**Тест:** «Есть ли папки Empire и Life? Ничего не меняй.»

Подробности: `docs/obsidian_geminese_setup_ru.md` (игнорируйте там про `git clone` на ПК).

---

## Блок 2 — TickTick (30 мин)

### 2.1 Экспорт

Только [ticktick.com](https://ticktick.com) в браузере:

**Аватар → Настройки → Аккаунт → Резервное копирование → Создать → CSV.**

Сохранить:

```text
F:\YandexDisk\obsidian (2)\Life\tasks\_import\ticktick-backup.csv
```

### 2.2 В Obsidian

**Вариант А — скрипт** (если скопировали `Life/tools/ticktick_csv_to_obsidian.py`):

```powershell
cd "$env:USERPROFILE"
python -m venv "$env:USERPROFILE\.venv-life"
.\.venv-life\Scripts\Activate.ps1
pip install python-dateutil
python "$VAULT\Life\tools\ticktick_csv_to_obsidian.py" `
  "$VAULT\Life\tasks\_import\ticktick-backup.csv" `
  "$VAULT\Life\tasks\inbox.md"
```

**Вариант Б — без Python:** открыть CSV в Excel, активные задачи (Status=0) вручную в `inbox.md`:

```markdown
- [ ] Название 📅 2026-06-01 #тег
```

### 2.3 Напоминания на телефоне

**Tasks.org** — срочное с временем; полный список — Obsidian `Life/tasks/`.

---

## Блок 3 — Диктофон

**Рекомендуется (без ПК):** `docs/voice_pipeline_vps_ru.md` — Google Drive → VPS Whisper → `Life/` на Яндекс.Диске, таймер каждые 15 мин.

Ниже — устаревший ручной вариант через ПК (можно не делать).

### Easy Voice Recorder → Google Drive → Life (ручной мост на ПК)

Записи на ПК уже здесь:

```text
G:\Мой диск\Easy Voice Recorder\     ← Easy Voice Recorder (Google Drive)
F:\YandexDisk\obsidian (2)\Life\voice\raw\   ← сюда копируем, дальше Яндекс.Диск
```

Скопируйте в vault `Life/tools/` с VPS:

- `sync_evrec_to_life.ps1`
- `voice_to_obsidian.py`

**Только копирование (без расшифровки):**

```powershell
powershell -ExecutionPolicy Bypass -File "F:\YandexDisk\obsidian (2)\Life\tools\sync_evrec_to_life.ps1"
```

**Копирование + Whisper:**

```powershell
powershell -ExecutionPolicy Bypass -File "F:\YandexDisk\obsidian (2)\Life\tools\sync_evrec_to_life.ps1" -Transcribe
```

Скрипт переносит только **новые** `.mp3` (не перезаписывает уже скопированные). Старые «Моя запись 1…8» один раз уйдут в `raw\` при первом запуске.

### 3.1 Куда писать аудио (вручную)

```text
F:\YandexDisk\obsidian (2)\Life\voice\raw\
```

(Если без EVR — запись в Downloads → копировать в `raw\`.)

### 3.2 Расшифровка

```powershell
.\.venv-life\Scripts\Activate.ps1
pip install faster-whisper watchdog
python "$VAULT\Life\tools\voice_to_obsidian.py" --once
```

Один короткий `.m4a` в `raw\` перед запуском. Результат: `Life/inbox/…-voice.md`.

Без скрипта: расшифровка в любом Whisper/ИИ → вставить в новую заметку в `Life/inbox/` вручную.

---

## Что не делать

| Не нужно | Почему |
|----------|--------|
| Клонировать Empire на `C:\` | Боты на VPS; заметки в vault |
| Искать `main.py` на диске | Это pip/PyCharm, не ваш проект |
| Класть задачи в `Empire/` | Уедут на VPS в бота |
| Ждать, что `Life/` появится на VPS | Так задумано — только Яндекс.Диск |

---

## После вечера

- Задачи → `Life/tasks/`
- Голос → `Life/voice/raw/` → скрипт или вручную → `Life/inbox/`
- Посты → `Empire/*/queue/` как раньше
- Geminese — правки текстов на ПК

---

## Файлы на VPS (для копирования в vault, не на C:)

| Откуда (репозиторий на сервере) | Куда (vault на ЯД) |
|--------------------------------|---------------------|
| `templates/obsidian_plugins/geminese/*` | `.obsidian/plugins/geminese/` |
| `templates/obsidian_life_kit/*.py` | `Life/tools/` |
| `templates/geminese_empire_system_prompt.txt` | `Life/tools/` (удобно) |
