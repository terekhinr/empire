# Голос: Google Drive → VPS (Whisper) → Obsidian на Яндекс.Диске

**ПК в конвейере не участвует.** Только:

- телефон: Easy Voice Recorder → Google Drive;
- VPS: забирает аудио, расшифровывает, **маршрутизирует** `.md` в нужную папку vault;
- ПК/телефон: Obsidian + клиент Яндекс.Диска **только читают** готовые файлы.

Geminese по-прежнему на **ПК** (по желанию), когда садитесь править текст.

---

## Схема

```text
[Android] Easy Voice Recorder
              ↓ (авто)
[Google Drive]  Easy Voice Recorder/*.m4a
              ↓ rclone (каждые 15 мин)
[VPS]         data/voice_incoming/
              ↓ faster-whisper + voice_route.py
[VPS]         data/voice_vault_staging/{маршрут}/*.md
              Life/voice/transcribed/*.m4a
              ↓ rclone copy (push_paths из config)
[Яндекс.Диск]  obsidian (2)/…
              ↓ Яндекс.Диск
[ПК / телефон] Obsidian vault
```

| Что | Где |
|-----|-----|
| Посты Empire → Telegram | `Empire/pension/queue/` — как было |
| **Книга 1** «На пенсию никогда» | `База знаний/Книги/На-пенсию-никогда/заметки/` |
| **Книга 2** «Трупик майора» | `База знаний/Книги/Трупик-майора/заметки/` |
| Пост / идея канала | `Empire/pension/inbox/` |
| Статья / лонгрид | `Контент/Статьи/заметки-voice/` |
| Личное | `Life/inbox/` |
| Без префикса | `Входящие/` + `needs-routing` |

Аудио **всегда** в `Life/voice/transcribed/` (ссылка из любой заметки).

---

## Префиксы в диктофоне

| Скажите в начале | Маршрут | Книга / проект |
|------------------|---------|----------------|
| **книга один**, **на пенсию никогда**, **пенсия книга** | заметки к книге 1 | `book: neverretire` |
| **книга два**, **трупик майора**, **повесть** | заметки к книге 2 | `book: trupik-maiora` |
| **пенсия пост**, **канал пенсия** | пост канала | `Empire/pension/inbox` |
| **пенсия идея** | идея поста | `Empire/pension/inbox` |
| **статья ноль** … **статья четыре**, **дзен** | статья | `Контент/Статьи/заметки-voice` |
| **личное** | личное | `Life/inbox` |
| *(ничего)* | разобрать | `Входящие/` |

Имя файла (если можно): `book1-…`, `book2-…`, `pension-post-…`, `article-…`.

---

## Один раз на VPS

### 0. Папки vault

```bash
cd /root/projects/empire
bash scripts/voice_vault_setup.sh
sudo bash scripts/obsidian_rclone_push_vault.sh   # README и структура на Яндекс.Диск
```

### 1. Google Drive в rclone

```bash
sudo bash scripts/rclone_setup_gdrive.sh
# или: scripts/rclone_paste_gdrive_token.sh (токен с Windows)
rclone lsd "gdrive:Easy Voice Recorder"
```

### 2. Whisper

```bash
./venv/bin/pip install faster-whisper
./venv/bin/python -c "from faster_whisper import WhisperModel; print('ok')"
```

### 3. `/etc/empire/voice.env`

```bash
sudo cp deploy/voice.env.example /etc/empire/voice.env
sudo chmod 600 /etc/empire/voice.env
```

Содержимое (обычно менять не нужно):

```bash
VOICE_GDRIVE_REMOTE=gdrive
VOICE_GDRIVE_PATH="Easy Voice Recorder"
YANDEX_VAULT_PATH="obsidian (2)"
VOICE_WHISPER_MODEL=small
VOICE_WHISPER_DEVICE=cpu
VOICE_ROUTE_CONFIG=/root/projects/empire/data/voice_route_config.json
VAULT_STAGING=/root/projects/empire/data/voice_vault_staging
```

Пути с пробелами **обязательно в кавычках**.  
Яндекс.Диск для push уже настроен в `/etc/empire/rclone.env` (remote `yandex`) — голосовой пайплайн его подхватывает сам.

Проверка, что env читается:

```bash
set -a && source /etc/empire/voice.env && set +a
echo "vault=$YANDEX_VAULT_PATH staging=$VAULT_STAGING"
```

---

## Первый запуск: два действия руками (подробно)

После шагов 0–2 ниже — то, без чего конвейер **не заработает на ПК**, даже если VPS «вроде настроен».

### A. Отправить новые папки на Яндекс.Диск

**Зачем:** на VPS созданы `База знаний/Книги/…`, README в `Входящие/`, `Life/voice/` и т.д. Obsidian на ПК открывает vault с **Яндекс.Диска** — пока не сделаете push, в проводнике/Obsidian этих папок не будет.

**Команда (SSH на VPS):**

```bash
cd /root/projects/empire
sudo bash scripts/obsidian_rclone_push_vault.sh
```

Что делает скрипт: `rclone sync` всего `data/obsidian_vault/` → `yandex:obsidian (2)/`.  
Новые README и пустые папки появятся в облаке; **старые заметки на Диске не удаляются** (sync с VPS, но без агрессивной чистки личных веток).

**Успех в терминале:** в конце строка вида `Vault copied → yandex:obsidian (2)`.

**На ПК (через 1–5 мин):**

1. Дождаться синка клиента Яндекс.Диск.
2. В Obsidian проверить:
   - `База знаний/Книги/На-пенсию-никогда/заметки/`
   - `База знаний/Книги/Трупик-майора/заметки/`
   - `Входящие/README.md` с таблицей префиксов
3. Карта: `Empire/ГДЕ-ВСЁ.md` (обновлённая секция про голос).

**Если push упал:** проверьте `/etc/empire/rclone.env` — логин и [пароль приложения](https://id.yandex.ru/security/app-passwords). Тест:

```bash
rclone lsd "yandex:obsidian (2)"
```

---

### B. Починить Google Drive (OAuth для `gdrive`)

**Зачем:** телефон кладёт `.m4a` в Google Drive → папка **Easy Voice Recorder**. VPS забирает их через rclone remote `gdrive`. Сейчас типичная ошибка в логах:

```text
empty token found - please run "rclone config reconnect gdrive:"
```

Пока токен пустой, шаг pull в пайплайне падает, Whisper не запускается.

**Важно:** войти нужно в тот же Google-аккаунт, куда Easy Voice Recorder делает бэкап (часто личный Gmail).

#### Вариант B1 — прямо в SSH (проще)

```bash
cd /root/projects/empire
sudo bash scripts/rclone_connect_gdrive_oauth.sh
```

1. В терминале появится **длинная ссылка** — скопировать и открыть в браузере на телефоне или ПК.
2. Войти в Google → «Разрешить» доступ к Drive (read-only достаточно).
3. Google покажет **код** — скопировать целиком и **вставить в SSH**, Enter.
4. Скрипт сам запишет токен в `gdrive` и проверит папку.

**Проверка:**

```bash
rclone lsd "gdrive:Easy Voice Recorder"
```

Должен быть список файлов/подпапок (или пустой каталог, но **без** ошибки token).

Если папка называется иначе — посмотреть корень:

```bash
rclone lsd gdrive: | head -20
```

и поправить в `/etc/empire/voice.env` строку `VOICE_GDRIVE_PATH="…"`.

#### Вариант B2 — токен с Windows (если в SSH браузер неудобен)

**На Windows** (PowerShell, rclone установлен):

```powershell
rclone authorize "drive" --drive-scope drive.readonly
```

Скопировать **только одну строку JSON** `{...}` (без текста «Paste the following»).

**На VPS:**

```bash
nano /root/gdrive_token.json
# вставить одну строку JSON, сохранить
sudo bash /root/projects/empire/scripts/rclone_paste_gdrive_token.sh
```

Скрипт удалит временный файл после импорта.

#### После успешного B — включить автомат

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now voice-pipeline.timer
sudo systemctl start voice-pipeline.service
journalctl -u voice-pipeline.service -n 40 --no-pager
```

В логе ожидается: `Pull audio` → `Transcribing` → `copy -> obsidian (2)/…` → `Done`.

---

### C. Проверочная запись (конец «шага 3»)

1. На телефоне: Easy Voice Recorder → запись **10–15 сек**:  
   *«Книга один. Тестовая заметка для проверки пайплайна.»*
2. Дождаться синка в Google Drive (обычно 1–3 мин, зависит от приложения).
3. Подождать **до 15 мин** (таймер) или вручную:

```bash
sudo systemctl start voice-pipeline.service
```

4. На ПК в Obsidian (после синка Яндекс.Диск):

| Ожидаете | Путь |
|----------|------|
| `.md` с транскриптом | `База знаний/Книги/На-пенсию-никогда/заметки/` |
| имя файла | `…-voice-book-neverretire.md` |
| аудио | `Life/voice/transcribed/` |
| в YAML | `route: book-neverretire`, `book: neverretire` |

Если файл попал в `Входящие/` — Whisper не услышал префикс; говорите чётче в первые 3 секунды или переименуйте файл на `book1-test.m4a` до синка в Google.

---

### 4. Тест

```bash
sudo bash scripts/voice_vps_pipeline.sh
journalctl -u voice-pipeline.service -n 30
```

### 5. Таймер

```bash
sudo cp deploy/voice-pipeline.service deploy/voice-pipeline.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now voice-pipeline.timer
```

---

## Файлы в репозитории

| Файл | Назначение |
|------|------------|
| `scripts/voice_vps_pipeline.sh` | pull → whisper → push |
| `scripts/voice_vps_transcribe.py` | расшифровка |
| `scripts/voice_route.py` | маршрутизация + шаблон `.md` |
| `data/voice_route_config.json` | правила и push_paths |
| `scripts/voice_vault_setup.sh` | создать папки vault + staging |
| `deploy/voice-pipeline.timer` | каждые 15 мин |

Маршруты правятся в `data/voice_route_config.json` без изменения кода.

---

## Если Google Drive падает

```text
empty token found - please run "rclone config reconnect gdrive:"
```

Пока токен не обновлён, таймер будет логировать ошибку; Obsidian на ПК не получит новые файлы.

---

## ПК (не основной путь)

`Life/tools/sync_evrec_to_life.ps1` и `voice_to_obsidian.py` — запасной вариант. На VPS всё уже автоматизировано.
