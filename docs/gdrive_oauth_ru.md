# Google Drive для voice-pipeline (один раз)

Ошибка в логах:

```text
empty token found - please run "rclone config reconnect gdrive:"
```

Значит VPS **ещё не авторизован** в Google. Пока токена нет, `voice-pipeline` будет падать на шаге `Pull audio from Google Drive`.

**Таймер лучше не включать**, пока не пройдёт проверка ниже.

---

## Способ A — в SSH на VPS (проще, если есть браузер под рукой)

```bash
cd /root/projects/empire
sudo bash scripts/rclone_connect_gdrive_oauth.sh
```

1. В терминале появится **URL** — откройте на телефоне или ПК.
2. Войдите в **тот же Google**, куда Easy Voice Recorder заливает записи.
3. Разрешите доступ → **скопируйте код** → вставьте в SSH, Enter.

Проверка:

```bash
rclone lsd "gdrive:Easy Voice Recorder"
```

Должны увидеть файлы вроде `Моя запись 1.mp3`.

Затем:

```bash
sudo systemctl start voice-pipeline.service
journalctl -u voice-pipeline.service -n 20
sudo systemctl enable --now voice-pipeline.timer
```

---

## Способ B — с Windows (если в SSH неудобно вставить код)

На **ПК** (установите [rclone for Windows](https://rclone.org/downloads/) или `winget install Rclone.Rclone`):

```powershell
rclone authorize "drive" --drive-scope drive.readonly
```

Скопируйте **только JSON** — одна строка от `{` до `}`.

**Не копируйте** текст `Paste the following into your remote machine` и стрелки `---`.

На VPS:

```bash
nano /root/gdrive_token.json
# вставить ТОЛЬКО JSON, сохранить Ctrl+O Enter Ctrl+X

sudo bash /root/projects/empire/scripts/rclone_paste_gdrive_token.sh
```

Или одной командой (если файл уже есть):

```bash
rclone config set gdrive token "$(cat /root/gdrive_token.json)" --config /root/.config/rclone/rclone.conf
rclone lsd "gdrive:Easy Voice Recorder"
```

**Неправильно** (так делать не надо):

```bash
rclone config set gdrive token {"access_token":...}   # сломается
```

---

## Исправление voice.env (уже на VPS)

Пути с пробелами **в кавычках**:

```ini
VOICE_GDRIVE_PATH="Easy Voice Recorder"
YANDEX_LIFE_PATH="obsidian (2)/Life"
```

Без кавычек была ошибка `Voice: command not found`.
