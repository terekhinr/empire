# Cursor ↔ VPS: SSH без пароля и восстановление после обрыва

Рабочая папка на VPS: `/root/projects/empire`  
Хост: `193.233.232.48` · пользователь: `root`

## Что может и не может агент

| Ситуация | Поведение |
|----------|-----------|
| Обрыв Remote SSH в Cursor | Сессия IDE и чат **прерываются**. Агент **не** переподключается сам. |
| Вы снова открыли VPS в Cursor | Напишите «продолжи» — агент читает чекпоинты, `git status`, незакоммиченные файлы. |
| Долгая команда на VPS (`pytest`, деплой) | Запускайте в **tmux** — процесс переживёт обрыв SSH (контекст чата всё равно восстановите вручную). |
| Задача без живой SSH-сессии | **Cursor Cloud Agent** (облако) или таймер systemd на VPS. |

**Пароль root для входа с ПК в репозиторий не кладём** — ни в `.env`, ни в `docs/`, ни в `.cursor/rules/`. Секреты сервисов на VPS: `/etc/empire/*.env` (`chmod 600`).

---

## 1. Один раз на ПК: ключ вместо пароля

### Вариант A — скрипт (PowerShell)

```powershell
cd "F:\YandexDisk\obsidian (2)\Life\tools"   # или путь к клону empire
powershell -ExecutionPolicy Bypass -File scripts\cursor_vps_ssh_setup_pc.ps1
```

Скрипт: создаёт `ed25519`-ключ (если нет), дописывает блок в `%USERPROFILE%\.ssh\config`, выводит публичный ключ.

### Вариант B — вручную

**Ключ:**

```powershell
ssh-keygen -t ed25519 -C "cursor-pc" -f $env:USERPROFILE\.ssh\id_ed25519
```

**Публичный ключ на VPS** (пароль root спросит **в последний раз**):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@193.233.232.48 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

**Проверка:**

```powershell
ssh empire-vps "hostname && cd /root/projects/empire && pwd"
```

Должно войти **без пароля**.

### SSH config на ПК

Шаблон: `deploy/cursor_ssh_config_pc.example` → скопировать в `C:\Users\<вы>\.ssh\config`.

```sshconfig
Host empire-vps
    HostName 193.233.232.48
    User root
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 30
    ServerAliveCountMax 6
    TCPKeepAlive yes
```

В Cursor: **Remote-SSH: Connect to Host…** → `empire-vps`.

### Если без ключа — только на ПК

Windows: **Панель управления → Учётные записи → Диспетчер учётных данных → Учётные данные Windows** → запись `root@193.233.232.48`.  
Не коммитить, не класть в Obsidian/Диск.

---

## 2. После обрыва связи

1. Cursor → переподключить **empire-vps** (или Reload Window).
2. В чате: `продолжи задачу X` или `смотри docs/gdepar_checkpoints.md`.
3. Агент смотрит:
   - `docs/gdepar_checkpoints.md` — последний CP;
   - `git status` / `git diff`;
   - `docs/EMPIRE_PIPELINE_CHECKLIST.md` при крупных задачах.
4. Длинные shell-команды — в tmux:

```bash
tmux new -s empire -c /root/projects/empire
# ... работа ...
# detach: Ctrl+B, D
# после обрыва SSH:
tmux attach -t empire
```

---

## 3. Связанные документы

| Документ | Зачем |
|----------|--------|
| `docs/obsidian_vps_workflow_ru.md` | Агент на VPS ↔ Obsidian |
| `docs/gdepar_checkpoints.md` | Статус выката gdepar |
| `docs/YANDEX_RCLONE_START.md` | Бэкап VPS, rclone (секреты в `/etc/empire/rclone.env`) |
| `deploy/README.md` | Деплой gdepar |

---

*Обновлено: 2026-06-19*
