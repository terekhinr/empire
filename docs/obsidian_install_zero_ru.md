# Obsidian + ИИ — установка с нуля (без заморочек)

**Время:** ~40 минут. **Репозиторий Empire на ПК не нужен.**  
**Geminese (плагин в Obsidian) — не ставим** — на Windows сутками ломается. ИИ — в терминале рядом с Obsidian.

---

## Что получится

| Нужно | Как |
|-------|-----|
| Заметки, Empire, Life | Obsidian, vault `F:\YandexDisk\obsidian (2)` |
| Найти слово в заметках | Obsidian **Ctrl+Shift+F** |
| Спросить ИИ по всему vault | Терминал: `gemini` (рядом с Obsidian) |
| Задачи вместо TickTick | Плагин **Tasks** (позже) |

---

## Шаг 1 — Obsidian и vault (5 мин)

1. Скачать Obsidian: https://obsidian.md/download  
2. Установить, запустить.  
3. **Open folder as vault** → выбрать:  
   `F:\YandexDisk\obsidian (2)`  
4. Если папки нет — создайте в Яндекс.Диске и снова откройте.

---

## Шаг 2 — Папки Life (5 мин)

PowerShell — скопировать блок целиком, Enter:

```powershell
$V = "F:\YandexDisk\obsidian (2)"
@(
  "Life\tasks\_import",
  "Life\voice\raw",
  "Life\voice\transcribed",
  "Life\inbox",
  "Life\tools"
) | ForEach-Object { New-Item -ItemType Directory -Force -Path (Join-Path $V $_) | Out-Null }

@'
# Inbox

## Без срока

'@ | Set-Content (Join-Path $V "Life\tasks\inbox.md") -Encoding utf8
```

В Obsidian: **Settings** (шестерёнка) → **Community plugins** → **Turn on community plugins** → **Browse** → найти **Tasks** → **Install** → **Enable**.

---

## Шаг 3 — Node.js (5 мин)

1. https://nodejs.org/ → кнопка **LTS** → скачать Windows Installer.  
2. Установить: **Next** → галочка **Add to PATH** → **Next** до конца.  
3. Закрыть все окна PowerShell, открыть **новое** PowerShell:

```powershell
node -v
```

Должно показать `v20...` или `v22...`. Если «не найдено» — переустановить Node с галочкой PATH.

---

## Шаг 4 — Gemini в терминале (10 мин)

```powershell
npm install -g @google/gemini-cli
cd "F:\YandexDisk\obsidian (2)"
gemini
```

Откроется чёрное окно CLI. **Первый раз** спросит вход:

### Вариант А (проще) — Google-аккаунт

- Выберите вход **через Google** / **Login with Google** (как предложит программа).  
- Откроется браузер → войти в обычный Google.  
- **Никакого «ключа» вручную не нужно.**

### Вариант Б — API key (только если сами выбрали)

«Ключ» = длинная строка букв с сайта https://aistudio.google.com/apikey → **Create API key** → скопировать.  
В CLI: команда `/auth` → выбрать API key → вставить.  
**Для Obsidian-плагина не нужен**, если плагин не используете.

Внизу CLI должно быть: `Authenticated...` и путь workspace = ваш vault.

Проверка — напечатать и Enter:

```text
перечисли папки в корне vault одной строкой
```

Если ответил — **всё, ИИ установлен.**

---

## Шаг 5 — Как пользоваться каждый день

**Два окна:**

1. **Obsidian** — читать и править `.md`. Поиск: **Ctrl+Shift+F**.  
2. **PowerShell:**

```powershell
cd "F:\YandexDisk\obsidian (2)"
gemini
```

Примеры в `gemini`: «найди всё про пенсию», «кратко Empire/pension/...».

Закрыть CLI: **Ctrl+C** или `/quit`.

---

## Geminese — не ставить

Плагин **Geminese** в Obsidian на Windows часто не видит тот же вход, что терминал.  
Если уже ставили — **Settings → Community plugins → Geminese → выключить.**

Не вводить ничего в «Environment variables» и «Gemini CLI path» — это для продвинутой починки.

---

## Позже (не сегодня)

- TickTick → экспорт CSV с ticktick.com → `Life/tasks/_import/`  
- Голос → отложено  
- Empire-посты в Telegram → как было, через `Empire/` и VPS  

---

## Если `gemini` не запускается

```powershell
where.exe gemini
Get-Content "$env:APPDATA\npm\gemini.cmd"
```

Пришлите вывод этих двух команд — по ним видно, куда ставился CLI.
