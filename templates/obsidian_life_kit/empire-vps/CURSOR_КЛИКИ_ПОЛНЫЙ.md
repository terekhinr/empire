# Cursor + Tailscale: что нажимать (полные сценарии)

> Папка setup на ПК: `F:\YandexDisk\obsidian (2)\Life\tools\empire-vps\`  
> Полный техгайд: [`cursor_vps_tailscale_ru.md`](cursor_vps_tailscale_ru.md)

---

## Сценарий 0 — Подготовка (один раз, до Cursor)

1. **Яндекс.Диск** — дождаться синка (иконка в трее → Sync).
2. Проводник → `F:\YandexDisk\obsidian (2)\Life\tools\empire-vps\`
3. **Двойной клик** `УСТАНОВИТЬ_TAILSCALE.bat`
4. В чёрном окне:
   - если спросит ключ на VPS — **`Y`** + Enter, введите пароль root **один раз**
   - дождитесь строк **`OK:`** и **`Готово`**
5. **Tailscale** (иконка в трее Windows):
   - правый клик → если **Log in** — войти тем же аккаунтом, что на VPS
   - статус **Connected**

Проверка в PowerShell (не обязательно, но полезно):

```powershell
ssh empire-vps-ts "hostname && pwd"
```

Должно вывести `moderate-amethys…` и `/root/projects/empire` **без пароля**.

---

## Сценарий 1 — Успешное подключение в Cursor (норма)

### Шаг 1. Открыть Cursor на Windows

- Закройте старые окна Cursor к VPS (если зависли).
- Запустите **Cursor** с рабочего стола (не через браузер).

### Шаг 2. Connect via SSH

**Если видите стартовый экран** (Open project / Clone repo / Connect via SSH):

1. Нажмите **`Connect via SSH`**
2. В списке кликните **`empire-vps-ts`**  
   *(или **`aeza-server`** — после bat тоже Tailscale)*
3. Если спросит **Select platform** → **`Linux`**
4. Подождите 30 сек – 3 мин (первый раз ставит сервер на VPS)

**Если уже открыт локальный проект:**

1. Клавиша **`F1`**
2. Наберите: **`Connect to Host`**
3. Выберите **`Remote-SSH: Connect to Host...`**
4. Клик **`empire-vps-ts`**

### Шаг 3. Дождаться подключения

- Внизу слева: **`Opening Remote...`** → потом **`SSH: empire-vps-ts`**
- Может открыться **новое окно** Cursor — работайте в нём.

### Шаг 4. Открыть папку empire

1. Меню **`File`** → **`Open Folder...`**  
   *(или **`Файл`** → **`Открыть папку...`**)*
2. В поле пути вставьте:
   ```text
   /root/projects/empire
   ```
3. **`OK`** / **«Выбор папки»**
4. Диалог **Trust / Доверять авторам?** → **`Yes, I trust`** / **«Да»**

### Шаг 5. Проверка

| Где | Должно быть |
|-----|-------------|
| Низ слева | `SSH: empire-vps-ts` |
| Explorer слева | папки `docs`, `scripts`, `deploy`… |
| Терминал `` Ctrl+` `` | `root@moderate-amethys:~/projects/empire#` |

### Шаг 6. Чат с агентом

- **`Ctrl+L`** или иконка чата справа
- Пишите задачи как обычно

**Готово.** Это ваш рабочий режим.

---

## Сценарий 2 — Если НЕ получилось (полная последовательность)

Идите **по шагам сверху вниз**. Не перескакивайте.

---

### Блок A — bat не сработал или SSH не пингуется

1. Проводник → `F:\YandexDisk\obsidian (2)\Life\tools\empire-vps\`
2. **Ещё раз** двойной клик **`УСТАНОВИТЬ_TAILSCALE.bat`**
3. Tailscale трей → **Quit** → запустить Tailscale снова → **Log in**
4. **`Win+R`** → `powershell` → Enter:

```powershell
tailscale status
tailscale ping 100.84.19.35
ssh empire-vps-ts hostname
```

| Результат | Дальше |
|-----------|--------|
| `ssh` работает | → **Блок C** (Cursor) |
| `Permission denied` | bat ещё раз, на вопрос про ключ — **Y**, пароль root |
| `timed out` | Tailscale не Connected → войти в аккаунт; если не помогло → **Блок E** |
| `Host key verification failed` | см. **Блок D п.3** |

---

### Блок B — хоста нет в списке Cursor

1. **`F1`**
2. **`Remote-SSH: Open SSH Configuration File...`**
3. Выберите файл **`C:\Users\<ваш_логин>\.ssh\config`**
4. Должен быть блок `# BEGIN empire-tailscale-cursor` с `Host empire-vps-ts`
5. Если блока **нет** → снова **`УСТАНОВИТЬ_TAILSCALE.bat`**
6. Сохраните config (**Ctrl+S**), закройте
7. **`F1`** → **`Remote-SSH: Connect to Host...`**
8. Если списка нет — введите вручную: **`root@100.84.19.35`**

---

### Блок C — SSH в PowerShell OK, Cursor не подключается

1. **`F1`** → **`Remote-SSH: Kill VS Code Server on Host...`**
2. Выберите **`empire-vps-ts`** (или **`aeza-server`**)
3. **`F1`** → **`Remote-SSH: Connect to Host...`** → **`empire-vps-ts`**
4. Если снова ошибка:
   - **`F1`** → **`Remote-SSH: Show Log`**
   - Скопируйте последние 20 строк — можно вставить агенту в чат
5. PowerShell:

```powershell
ssh empire-vps-ts "rm -rf ~/.cursor-server ~/.vscode-server"
```

6. В Cursor снова **`F1`** → **`Connect to Host...`** → **`empire-vps-ts`**

---

### Блок D — ошибки при первом подключении

**D1. «Could not establish connection» / зависает на Installing**

1. **`F1`** → **Kill VS Code Server on Host** → `empire-vps-ts`
2. PowerShell (команда выше — удалить cursor-server)
3. **`F1`** → **Connect to Host...** → `empire-vps-ts`
4. Подождать до 5 мин

**D2. Спрашивает пароль каждый раз**

1. **`Win+R`** → `control /name Microsoft.CredentialManager`
2. **Учётные данные Windows** → удалить записи `root@193.233.232.48`, `root@100.84.19.35`
3. Снова **`УСТАНОВИТЬ_TAILSCALE.bat`**

**D3. «Host key verification failed»**

PowerShell:

```powershell
ssh-keygen -R 100.84.19.35
ssh-keygen -R 193.233.232.48
```

Снова Connect to Host.

---

### Блок E — Tailscale не помогает (запасной путь)

1. **`F1`** → **`Remote-SSH: Connect to Host...`**
2. Выберите **`empire-vps`** *(публичный IP, может рваться чаще)*
3. **`File` → `Open Folder...`** → `/root/projects/empire`
4. Долгие команды на VPS только в **tmux** (см. основной гайд)

---

### Блок F — подключились, но оборвалось / пустой чат

1. **`F1`** → **`Remote-SSH: Reload Window`**
2. Если не помогло — **`Connect to Host...`** → **`empire-vps-ts`**
3. **`File` → `Open Folder...`** → `/root/projects/empire`
4. Чат агента: напишите **`продолжи`**

---

### Блок G — совсем ничего (попросить агента на VPS)

Если есть **хоть какой-то** SSH (Tailscale, empire-vps или телефон):

1. Подключитесь в Cursor как получится
2. Откройте `/root/projects/empire`
3. В чате:

```text
SSH не подключается через empire-vps-ts. Проверь tailscale, ssh, apply_vps_ssh_stability. Я на Windows, bat уже запускал.
```

4. Вставьте вывод (если есть):

```powershell
tailscale status
ssh -vvv empire-vps-ts
```

---

## Сценарий 3 — Полный ОТКАТ (вернуть как было)

### Часть 1 — Откат на ПК (Cursor + SSH config)

#### Вариант A — простой (рекомендуется)

1. **Закройте все окна Cursor**, подключённые к VPS  
   *(File → Exit / Alt+F4)*
2. Проводник → `F:\YandexDisk\obsidian (2)\Life\tools\empire-vps\`
3. **Двойной клик** **`ОТКАТ.bat`**
4. Дождитесь **`OK: удалён блок empire-tailscale-cursor`**

#### Вариант B — полный откат всего SSH config

1. Закройте Cursor
2. PowerShell:

```powershell
cd "F:\YandexDisk\obsidian (2)\Life\tools\empire-vps"
powershell -ExecutionPolicy Bypass -File .\cursor_vps_tailscale_rollback_pc.ps1 -RestoreLatestBackup
```

Восстановит `C:\Users\<вы>\.ssh\config` из `%USERPROFILE%\.ssh\empire-backup\`.

#### После отката на ПК — Cursor

1. Запустите Cursor
2. **`F1`** → **`Remote-SSH: Kill VS Code Server on Host...`** → выберите **`empire-vps-ts`** и **`aeza-server`** (если есть)
3. **`F1`** → **`Connect to Host...`**
4. Выберите **старый хост** — как подключались раньше, например **`aeza-server`** или **`empire-vps`**
5. **`File` → `Open Folder...`** → `/root/projects/empire`

Tailscale на ПК **можно не удалять** — он просто не будет использоваться для SSH.

---

### Часть 2 — Откат на VPS (только если просили / агент)

Подключитесь к VPS любым способом, терминал:

```bash
bash /root/projects/empire/scripts/rollback_vps_tailscale_ssh.sh
```

Полный откат + выключить Tailscale SSH на VPS:

```bash
bash /root/projects/empire/scripts/rollback_vps_tailscale_ssh.sh --disable-tailscale-ssh
```

После этого снова **`Connect to Host...`** → старый хост (`empire-vps` / `aeza-server`).

---

### Часть 3 — Проверка после отката

| Проверка | Ожидание |
|----------|----------|
| `~\.ssh\config` | нет блока `# BEGIN empire-tailscale-cursor` |
| Cursor | подключается старым хостом (как до эксперимента) |
| Tailscale в трее | может оставаться включённым — это нормально |

---

## Шпаргалка: команды Cursor (F1)

| Что нужно | Набрать в F1 |
|-----------|----------------|
| Подключиться | `Remote-SSH: Connect to Host...` |
| Перезагрузить окно | `Remote-SSH: Reload Window` |
| Убить сервер на VPS | `Remote-SSH: Kill VS Code Server on Host...` |
| Лог ошибок | `Remote-SSH: Show Log` |
| SSH config | `Remote-SSH: Open SSH Configuration File...` |
| Продолжить задачу | в **чате**: `продолжи` |

---

*Обновлено: 2026-06-21*
