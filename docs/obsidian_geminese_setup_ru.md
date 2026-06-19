# Geminese в Obsidian (ПК) — установка под Empire

**Только desktop:** Windows / macOS / Linux. На телефоне geminese **не работает**.

**Репозиторий Empire на ПК не нужен.** Vault на Яндекс.Диске (`F:\YandexDisk\obsidian (2)\`). Три файла плагина копируете в `.obsidian\plugins\geminese\` с VPS или с GitHub. Вечерний порядок: `docs/obsidian_evening_setup_ru.md`.

Плагин в репозитории на VPS: `templates/obsidian_plugins/geminese/` (версия **0.9.1**).

---

## 1. Gemini CLI (обязательно до Obsidian)

### Windows (ваш ПК: `F:\YandexDisk\obsidian (2)\`)

1. Установите **Node.js LTS** с [nodejs.org](https://nodejs.org/) — галочка **Add to PATH**.
2. Откройте **PowerShell** (не обязательно от админа):

```powershell
npm install -g @google/gemini-cli
gemini
```

3. При первом запуске `gemini` — войдите в **Google-аккаунт** в браузере (free tier достаточно).
4. Проверка:

```powershell
where.exe gemini
gemini -p "Ответь одним словом: ок"
```

`where.exe gemini` показывает **gemini.cmd** — для терминала. В **Geminese** указывают **реальный .js из установки** (плагин запускает через `node`), не `.cmd`.

Сначала узнайте путь (не угадывайте):

```powershell
where.exe gemini
Get-Content (where.exe gemini | Select-Object -First 1)
npm root -g
```

**Gemini CLI 0.43+** (у вас в терминале была v0.43.0) — точка входа **`bundle/gemini.js`**, не `dist/index.js`:

```powershell
Test-Path "$env:APPDATA\npm\node_modules\@google\gemini-cli\bundle\gemini.js"
```

Если `True`, в Geminese вставьте:

```text
C:\Users\Destroy\AppData\Roaming\npm\node_modules\@google\gemini-cli\bundle\gemini.js
```

Старые версии npm-пакета использовали `dist\index.js` — проверяйте `Get-Content` на `gemini.cmd`, там будет фактический путь.

### macOS / Linux

```bash
npm install -g @google/gemini-cli
which gemini
gemini -p "ok"
```

---

## 2. Установка плагина geminese в vault

Vault на ПК: **`F:\YandexDisk\obsidian (2)\`** (корень vault, не только `Empire/`).

### Способ A — вручную (обычный для Яндекс.Диска)

1. Создайте папку:

```text
F:\YandexDisk\obsidian (2)\.obsidian\plugins\geminese\
```

2. Скопируйте **три файла** из репозитория Empire:

```text
templates/obsidian_plugins/geminese/main.js
templates/obsidian_plugins/geminese/manifest.json
templates/obsidian_plugins/geminese/styles.css
```

3. В Obsidian: **Settings → Community plugins → Turn on community plugins** (если ещё не включено).

4. **Settings → Community plugins → Reload** (или перезапустите Obsidian).

5. В списке плагинов включите **Geminese**.

### Способ B — скрипт (только если есть клон Empire на ПК)

```powershell
.\scripts\install_geminese_windows.ps1
```

### Способ C — BRAT (обновления с GitHub)

1. Плагин **BRAT** → Add beta plugin: `https://github.com/Momoyu404/geminese`
2. Всё равно нужен **Gemini CLI** (шаг 1).

---

## 3. Настройка Geminese под Empire

**Settings → Geminese:**

| Поле | Значение |
|------|----------|
| **Gemini CLI path** | Пусто (авто) или **.js из `Get-Content gemini.cmd`** (см. шаг 1) |
| **Permission mode** | Сначала **Plan** (только читает); для правок файлов — **Agent** |
| **Working directory** | По умолчанию = корень vault (правильно) |

Откройте vault с корнем `obsidian (2)`, чтобы агент видел и `Empire/`, и daily notes.

### Инструкция для чата (вставьте в первое сообщение или Custom instructions плагина)

Файл в репозитории: `templates/geminese_empire_system_prompt.txt`

Кратко:

- Посты в канал → только `Empire/*/queue/` + YAML (`persona`, `scheduled`, `status`).
- `status: ready` — только по явной просьбе.
- Не трогать `_canvas/`, `published/`.
- Задачи → `Empire/_tasks/` (если папка есть).
- `scheduled` — часовой пояс **Москва**.

---

## 4. Проверка, что всё работает

1. Obsidian → иконка Geminese (боковая панель) → новый чат.
2. Сообщение: `Какая у тебя рабочая папка? Перечисли папки в Empire/ одним уровнем.`
3. Если ошибка **Gemini CLI not found** → укажите путь в **Advanced → Gemini CLI path**.
4. Тест Plan: `Прочитай Empire/pension/_scenarios/growth-rf-2026.md и назови 3 невыполненных пункта из секции Неделя` (путь подстройте под vault).

---

## 5. Связка с Empire (не ломать)

```text
Вы + geminese (ПК)  →  правите .md в Empire/
Яндекс.Диск sync     →  rclone на VPS
Empire               →  queue/ status:ready → Telegram approve
```

- Не редактируйте один и тот же файл в `queue/` одновременно на ПК и на VPS.
- После правок в `queue/` с `status: ready` — дождитесь sync (~10–15 мин) или `/obsidian import` в боте.

---

## 6. Типичные ошибки

| Симптом | Решение |
|---------|---------|
| `spawn ...\npm\gemini ENOENT` | **Gemini CLI path** → путь к **.js** из `Get-Content ...\gemini.cmd` (0.43+: `bundle\gemini.js`). Не `gemini.cmd`. Перезапуск Obsidian |
| `Path does not exist` в настройках | Путь обрезан или неверный файл — скопировать из `Get-Content gemini.cmd` целиком |
| CLI not found | `npm install -g @google/gemini-cli` → снова `Test-Path` на путь из `gemini.cmd` |
| Плагин не в списке | Проверить три файла в `.obsidian/plugins/geminese/` |
| `GEMINI_API_KEY` + «folder is not trusted» | См. **§6.1** ниже |
| Пустой ответ / auth | Снова `gemini` в терминале, залогиниться |
| Агент «ломает» frontmatter | Режим Plan; явно «не меняй YAML между ---» |
| Mobile | geminese недоступен — Obsidian + Tasks или Gemini Scribe |

---

## 6.0. Geminese не заводится — нормально

На Windows с **API key** плагин часто не видит ключ и trust, хотя `gemini` в терминале работает.

**Рабочая схема без плагина:**

1. **Obsidian** — обычный поиск `Ctrl+Shift+F` по vault.
2. **Терминал** — `cd "F:\YandexDisk\obsidian (2)"` → `gemini` → вопросы по заметкам.

Плагин Geminese можно **выключить** и не тратить время.

Последняя попытка для плагина — **launcher** (§6.1a), не повторять ввод ключа в UI Geminese.

### 6.1a. Launcher (один файл)

1. Скопировать `templates/obsidian_life_kit/geminese-launcher.js` →  
   `C:\Users\Destroy\.gemini\geminese-launcher.js`
2. Файл `C:\Users\Destroy\.gemini\.env` с одной строкой:  
   `GEMINI_API_KEY=ваш_ключ`
3. **Geminese → Gemini CLI path** → путь к **geminese-launcher.js** (не bundle/gemini.js).
4. Перезапуск Obsidian.

---

## 6.1. Один раз на ПК (переменные Windows)

В PowerShell **один блок** — ключ подставьте свой (из [AI Studio](https://aistudio.google.com/apikey)):

```powershell
$vault = "F:\YandexDisk\obsidian (2)"
$gemini = "$env:USERPROFILE\.gemini"
New-Item -ItemType Directory -Force -Path $gemini | Out-Null

@{
  $vault = "TRUST_FOLDER"
} | ConvertTo-Json | Set-Content "$gemini\trustedFolders.json" -Encoding utf8

@"
GEMINI_API_KEY=ВСТАВЬТЕ_КЛЮЧ
"@ | Set-Content "$gemini\.env" -Encoding utf8

[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "ВСТАВЬТЕ_КЛЮЧ", "User")
[System.Environment]::SetEnvironmentVariable("GEMINI_CLI_TRUST_WORKSPACE", "true", "User")
```

**Выйти из Obsidian полностью** → запустить снова (лучше перезагрузить Windows один раз).  
В Geminese поле Environment variables можно **оставить пустым**.

Проверка:

```powershell
cd $vault
gemini -p "ответь: ок"
```

---

## 6.2. Ошибка: `GEMINI_API_KEY` и «folder is not trusted» (подробно)

CLI в **терминале** уже залогинен, а **Geminese** запускает отдельный процесс из корня vault. Папка vault **не trusted** → не подхватывается `.env`, режим сбрасывается в default → просит `GEMINI_API_KEY`.

**Шаг A — доверить vault (один раз):**

```powershell
cd "F:\YandexDisk\obsidian (2)"
gemini
```

В интерактивном CLI: `/permissions` или диалог при старте → **Trust folder** (или «Trust parent» для `F:\YandexDisk\`).

Либо в **Settings → Geminese → Environment variables** (блок внизу, многострочное поле):

```text
GEMINI_CLI_TRUST_WORKSPACE=true
```

**Шаг B — ключ для Obsidian** (если в терминале auth через API key):

1. Ключ: [Google AI Studio](https://aistudio.google.com/apikey) (тот же, что при `gemini` /auth).
2. В том же поле **Environment variables** в Geminese:

```text
GEMINI_API_KEY=ваш_ключ_без_кавычек
GEMINI_CLI_TRUST_WORKSPACE=true
```

3. Клик вне поля (сохранение на blur) → **полный перезапуск Obsidian**.

Проверка в PowerShell из vault (должен ответить без ошибки auth):

```powershell
cd "F:\YandexDisk\obsidian (2)"
$env:GEMINI_API_KEY="ваш_ключ"
$env:GEMINI_CLI_TRUST_WORKSPACE="true"
gemini -p "ответь: ок"
```

Ключ **не** коммитьте в git и не кладите в заметки vault — только настройки плагина или `%USERPROFILE%\.gemini\.env`.

---

## 7. Обновление плагина

```powershell
cd F:\путь\к\empire
git pull
.\scripts\install_geminese_windows.ps1
```

Или BRAT → Update plugin.

Перекачать файлы в репозиторий (на VPS/в git):

```bash
./scripts/fetch_geminese_plugin.sh
```

---

## Файлы

| Путь | Назначение |
|------|------------|
| `templates/obsidian_plugins/geminese/` | Сборка плагина 0.9.1 |
| `scripts/install_geminese_windows.ps1` | Копирование в vault Windows |
| `scripts/fetch_geminese_plugin.sh` | Скачать новый релиз в repo |
| `templates/geminese_empire_system_prompt.txt` | Промпт для Empire |

См. также: `docs/obsidian_practical_guide_ru.md`, `docs/obsidian_sync_vps_ru.md`, **`docs/obsidian_evening_setup_ru.md`** (вечерний сетап: Geminese + TickTick + голос).
