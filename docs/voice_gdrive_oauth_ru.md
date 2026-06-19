# Google Drive для голосового пайплайна — пошагово

**Проблема на скриншоте:** в PowerShell на Windows команда `rclone` не найдена — **rclone на ПК не установлен**.  
Для настройки **Windows не нужен**. Достаточно SSH на VPS + браузер на телефоне.

---

## Что уже работает (трогать не надо)

| Готово | Где |
|--------|-----|
| Папки книг, README | Яндекс.Диск → `obsidian (2)/База знаний/Книги/…` |
| Whisper + маршруты | VPS |
| Таймер каждые 15 мин | `voice-pipeline.timer` |
| Заметки → Obsidian | через Яндекс.Диск |

**Не работает одно:** VPS не может **зайти в ваш Google Drive** и скачать папку **Easy Voice Recorder**.  
Пока не привяжете Google — записи с телефона не попадут в Obsidian.

---

## Способ A (рекомендуется) — только SSH + браузер

**Ничего не ставить на Windows.**

### Шаг 1. Откройте терминал VPS

В Cursor: **Terminal → SSH к серверу** (тот же, где Empire), или PuTTY.

### Шаг 2. Запустите скрипт

```bash
cd /root/projects/empire
sudo bash scripts/rclone_connect_gdrive_oauth.sh
```

### Шаг 3. Появится длинная ссылка

Примерно так:

```text
https://accounts.google.com/o/oauth2/auth?client_id=...
```

- Скопируйте **всю** ссылку.
- Откройте на **телефоне** или в Chrome на ПК.
- Войдите в **тот Google-аккаунт**, куда Easy Voice Recorder складывает записи.
- Нажмите **Разрешить** / **Allow**.

### Шаг 4. Google покажет код

Страница с текстом вроде «Please copy this code…» и строкой:

```text
4/0AeanS...
```

- Скопируйте код **целиком**.
- Вернитесь в **SSH-терминал** (он ждёт ввода).
- **Вставьте** код → Enter.

### Шаг 5. Успех

В терминале должно быть:

```text
Test:
          -1 2026-…        -1 Easy Voice Recorder
OK.
```

Если папка называется иначе — напишите, поправим `VOICE_GDRIVE_PATH` в `/etc/empire/voice.env`.

### Шаг 6. Запуск

```bash
sudo systemctl start voice-pipeline.service
journalctl -u voice-pipeline.service -n 20 --no-pager
```

В логе: `Pull audio` → `Transcribing` или `No new audio` — **без** `empty token`.

### Шаг 7. Проверка с телефона

1. Запись 10 сек: *«Книга один. Тест.»*
2. Подождать синк в Google Drive (1–3 мин).
3. Через 15 мин (или `sudo systemctl start voice-pipeline.service`).
4. В Obsidian: `База знаний/Книги/На-пенсию-никогда/заметки/`.

---

## Способ B — через Windows (только если хотите)

Нужен **rclone на ПК**. Сейчас его нет — отсюда ошибка на скриншоте.

### B1. Установить rclone

1. https://rclone.org/downloads/
2. **Windows AMD64** → zip.
3. Распаковать, положить `rclone.exe` например в `C:\Tools\rclone\`.
4. PowerShell **от администратора** (один раз):

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Tools\rclone", "User")
```

Закрыть PowerShell, открыть заново. Проверка:

```powershell
rclone version
```

### B2. Получить токен

```powershell
rclone authorize "drive" --drive-scope drive.readonly
```

Откроется браузер → разрешить доступ. В окне PowerShell появится **одна строка JSON**:

```json
{"access_token":"...","token_type":"Bearer",...}
```

Скопировать **только JSON**, от `{` до `}`.

### B3. На VPS

```bash
nano /root/gdrive_token.json
```

Вставить одну строку JSON → Ctrl+O → Enter → Ctrl+X.

```bash
sudo bash /root/projects/empire/scripts/rclone_paste_gdrive_token.sh
```

---

## Если что-то пошло не так

| Симптом | Что делать |
|---------|------------|
| `empty token found` | Повторить способ A |
| `directory not found` для Easy Voice Recorder | `rclone lsd gdrive:` — как реально называется папка |
| Заметка в `Входящие/` | Говорить префикс в первые 3 сек: «книга один» |
| На ПК нет новых папок | Подождать синк Яндекс.Диска 5–10 мин |

---

## Схема одной строкой

```text
Телефон (диктофон) → Google Drive → [НУЖЕН OAuth] → VPS → Whisper → Яндекс → Obsidian
                              ↑
                         вы здесь
```

После OAuth цепочка замкнётся сама.
