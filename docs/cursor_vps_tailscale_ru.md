# Cursor ↔ VPS через Tailscale — полный гайд

> **Зачем этот файл:** стабильное подключение Cursor Remote SSH к Empire VPS без обрывов каждые 2–4 минуты.  
> **Обновлено:** 2026-06-21  
> **VPS:** `moderate-amethys` · Tailscale `100.84.19.35` · публичный IP `193.233.232.48`  
> **Рабочая папка на VPS:** `/root/projects/empire`  
> **Копия в Obsidian:** `Life/tools/cursor_vps_tailscale_ru.md` (Яндекс.Диск)

---

## Содержание

1. [[#Зачем Tailscale, а не прямой IP]]
2. [[#Схема подключения]]
3. [[#Что нужно один раз]]
4. [[#Шаг 1 — Tailscale на ПК]]
5. [[#Шаг 2 — SSH-ключ]]
6. [[#Шаг 3 — SSH config]]
7. [[#Шаг 4 — Cursor Remote SSH]]
8. [[#Проверка что всё работает]]
9. [[#Если ничего не получается — самодиагностика]]
10. [[#Починить самому — типовые поломки]]
11. [[#Помощь агента Cursor — когда и как]]
12. [[#Запасной путь без Tailscale]]
13. [[#Шпаргалка команд]]

---

## Зачем Tailscale, а не прямой IP

| Путь | Адрес | Что происходит | Стабильность |
|------|-------|----------------|--------------|
| **Tailscale (рекомендуется)** | `empire-vps-ts` → `100.84.19.35` | ПК и VPS соединяются **напрямую** по WireGuard mesh | Высокая |
| Прямой IP / `empire-vps` | `193.233.232.48` | Трафик идёт через Keenetic → xray-туннель на VPS → обратно на sshd | Низкая |

**Почему рвётся прямой IP:** SSH с ПК часто идёт *через тот же VPN (xray)*, который крутится на VPS. При рестарте xray или NAT на роутере Keenetic (~4 мин idle) сессия Cursor обрывается. В логах VPS это выглядит как `Connection reset by peer` с IP `79.139.217.172` (WAN Keenetic).

**Tailscale решает:** создаёт отдельный зашифрованный канал `ПК (100.71.232.75) ↔ VPS (100.84.19.35)`, **минуя xray и NAT роутера**.

---

## Схема подключения

```text
┌─────────────┐     WireGuard mesh      ┌──────────────────┐
│  Windows ПК │ ◄──────────────────────►│  VPS moderate-   │
│  Tailscale  │   100.71 ↔ 100.84       │  amethys         │
│  Cursor IDE │                         │  /root/projects/ │
└─────────────┘                         │  empire          │
       │                                └──────────────────┘
       │  НЕ использовать для SSH:
       ▼
┌─────────────┐   xray/VPN   ┌─────────┐
│  Keenetic   │ ────────────►│  VPS    │  ← рвётся при рестарте xray
└─────────────┘              └─────────┘
```

**Правило:** в Cursor всегда выбирать хост **`empire-vps-ts`**, не `empire-vps` и не голый IP.

---

## Что нужно один раз

- [ ] Аккаунт Tailscale (у вас: `potertiy@…`, tailnet `tailed4746.ts.net`)
- [ ] Tailscale установлен и **включён** на Windows (`win-2ik85aj86aq`)
- [ ] SSH-ключ `ed25519` на ПК (`%USERPROFILE%\.ssh\id_ed25519`)
- [ ] Блок `Host empire-vps-ts` в `%USERPROFILE%\.ssh\config`
- [ ] Cursor с расширением **Remote - SSH**
- [ ] Публичный ключ добавлен в `/root/.ssh/authorized_keys` на VPS

---

## Шаг 1 — Tailscale на ПК

### Автоматически (рекомендуется)

Двойной клик или PowerShell из **`F:\Media Empire`**:

```powershell
cd "F:\Media Empire"
powershell -ExecutionPolicy Bypass -File scripts\cursor_vps_tailscale_setup_pc.ps1 -InstallTailscale
```

Или двойной клик: `scripts\install_cursor_tailscale_pc.bat`

Скрипт: проверяет Tailscale, бэкапит `~\.ssh\config`, добавляет `empire-vps-ts` и **переключает `aeza-server` на Tailscale**, копирует SSH-ключ на VPS.

**Откат на ПК:** `scripts\rollback_cursor_tailscale_pc.bat` или `cursor_vps_tailscale_rollback_pc.ps1`

**На VPS (уже можно):** `bash scripts/apply_vps_tailscale_ssh.sh` · откат: `bash scripts/rollback_vps_tailscale_ssh.sh`

### Установка вручную (если ещё нет)

1. Скачать: https://tailscale.com/download/windows
2. Установить, войти тем же аккаунтом, что и на VPS (`potertiy@…`).
3. В трее Windows — иконка Tailscale должна быть **Connected** (зелёная).

### Проверка в PowerShell

```powershell
tailscale status
```

Ожидаемый фрагмент:

```text
100.84.19.35   moderate-amethys  potertiy@  linux
100.71.232.75  win-2ik85aj86aq   potertiy@  windows
```

### Проверка связи с VPS

```powershell
tailscale ping moderate-amethys
# или
ping 100.84.19.35
```

> **Примечание:** обычный `ping` может не отвечать (Windows firewall), но `tailscale ping` должен показать `pong … in XXms`.

---

## Шаг 2 — SSH-ключ

### Автоматически (рекомендуется)

Откройте PowerShell. Путь к репозиторию empire — где он у вас лежит:

```powershell
cd "F:\Media Empire"
powershell -ExecutionPolicy Bypass -File scripts\cursor_vps_tailscale_setup_pc.ps1
```

Старый скрипт (только SSH, без Tailscale-проверок): `scripts\cursor_vps_ssh_setup_pc.ps1`

Скрипт:
- создаёт `%USERPROFILE%\.ssh\id_ed25519` (если нет);
- дописывает `empire-vps-ts` и `empire-vps` в `%USERPROFILE%\.ssh\config`;
- предложит скопировать ключ на VPS (пароль root — **последний раз**).

### Вручную

```powershell
ssh-keygen -t ed25519 -C "cursor-pc-empire" -f $env:USERPROFILE\.ssh\id_ed25519
```

Скопировать ключ на VPS (лучше через Tailscale IP):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@100.84.19.35 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### Проверка входа без пароля

```powershell
ssh empire-vps-ts "hostname && cd /root/projects/empire && pwd"
```

Должно вывести `moderate-amethys…` и `/root/projects/empire` **без запроса пароля**.

---

## Шаг 3 — SSH config

Файл: `C:\Users\<ваш_логин>\.ssh\config`

Шаблон из репозитория empire: `deploy/cursor_ssh_config_pc.example`

Минимально нужный блок:

```sshconfig
Host empire-vps-ts
    HostName 100.84.19.35
    User root
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 30
    ServerAliveCountMax 20
    TCPKeepAlive yes
    ConnectTimeout 60

Host moderate-amethys
    HostName moderate-amethys.tailed4746.ts.net
    User root
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 30
    ServerAliveCountMax 20
    TCPKeepAlive yes
    ConnectTimeout 60

Host empire-vps
    HostName 193.233.232.48
    User root
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 30
    ServerAliveCountMax 20
    TCPKeepAlive yes
    ConnectTimeout 60
```

---

## Шаг 4 — Cursor Remote SSH

**Подробно «что нажимать»:** [`docs/cursor_vps_tailscale_clicks_ru.md`](cursor_vps_tailscale_clicks_ru.md) — норма, если не работает, полный откат.

### Первое подключение (кратко)

1. Откройте Cursor на ПК.
2. `F1` → **Remote-SSH: Connect to Host…**
3. Выберите **`empire-vps-ts`** (не `empire-vps`!).
4. Дождитесь установки серверной части Cursor на VPS (первый раз — 1–3 мин).
5. **File → Open Folder** → `/root/projects/empire`

### Настройки keepalive

В проекте empire на VPS есть `.vscode/settings.json` с keepalive и путём к SSH config.

### Долгие команды — tmux

```bash
tmux new -s empire -c /root/projects/empire
# работа…
# отсоединиться: Ctrl+B, затем D
# после переподключения:
tmux attach -t empire
```

---

## Проверка что всё работает

| # | Проверка | Команда | Ожидание |
|---|----------|---------|----------|
| 1 | Tailscale на ПК | `tailscale status` | VPS `moderate-amethys` в списке |
| 2 | Связь mesh | `tailscale ping moderate-amethys` | `pong … in XXms` |
| 3 | SSH по ключу | `ssh empire-vps-ts hostname` | без пароля |
| 4 | Проект | `ssh empire-vps-ts "test -d /root/projects/empire && echo OK"` | `OK` |
| 5 | Cursor | Connect to Host → `empire-vps-ts` | открывается `/root/projects/empire` |
| 6 | IP в логах VPS | `journalctl -u ssh --since "5 min ago" \| grep Accepted` | IP **`100.71.232.75`**, не `79.139.217.172` |

Последний пункт — главный: IP `79.139.217.172` означает, что SSH идёт **через VPN**, а не Tailscale.

---

## Если ничего не получается — самодиагностика

Проходите **сверху вниз**.

### A. Tailscale не подключается на ПК

```powershell
tailscale status
tailscale netcheck
```

| Симптом | Действие |
|---------|----------|
| `Logged out` | войти в Tailscale заново |
| VPS не в списке | проверить email аккаунта |
| VPS `offline` | см. «Починить самому» п. 5 |
| только `relay` | для SSH нормально; `tailscale ping` должен работать |

### B. `ssh empire-vps-ts` — timeout / refused

```powershell
tailscale ping 100.84.19.35
Test-NetConnection 100.84.19.35 -Port 22
ssh -vvv empire-vps-ts
```

| Ошибка | Действие |
|--------|----------|
| `Connection timed out` | Tailscale на ПК выключен или VPS offline |
| `Permission denied (publickey)` | повторить шаг 2 (ключ) |
| `Host key verification failed` | `ssh-keygen -R 100.84.19.35` |

### C. SSH работает, Cursor — нет

1. `F1` → **Remote-SSH: Kill VS Code Server on Host** → `empire-vps-ts`
2. Переподключиться.
3. Output → Remote-SSH — скопировать ошибку.
4. На VPS: `df -h /` и `bash /root/projects/empire/scripts/cursor_orphan_cleanup.sh`

### D. Рвётся каждые несколько минут

Проверьте хост в Cursor — должен быть **`empire-vps-ts`**, не `empire-vps`.

---

## Починить самому — типовые поломки

### 1. Не тот хост в Cursor

**Лечение:** Connect to Host → **`empire-vps-ts`**.

### 2. SSH просит пароль

```powershell
powershell -ExecutionPolicy Bypass -File scripts\cursor_vps_ssh_setup_pc.ps1
```

Удалить старый пароль: Панель управления → Диспетчер учётных данных → `root@193.233.232.48`.

### 3. Tailscale Connected, но ping не идёт

1. Quit Tailscale → запустить снова.
2. `tailscale ping moderate-amethys` — главный тест.
3. Проверить Windows Firewall для Tailscale.

### 4. Cursor после обрыва — пустой чат

1. Remote-SSH: Reload Window
2. В чате: **`продолжи`**
3. Терминал: `tmux attach -t empire`

### 5. VPS полностью недоступен

1. Панель хостера → VNC-консоль
2. Или телефон с Tailscale: `ssh root@100.84.19.35`
3. На VPS:

```bash
systemctl restart tailscaled ssh
bash /root/projects/empire/scripts/apply_vps_ssh_stability.sh
```

### 6. Cursor не ставит server после обновления

```powershell
ssh empire-vps-ts "rm -rf ~/.cursor-server ~/.vscode-server"
```

### 7. Конфликт host keys

```powershell
ssh-keygen -R 100.84.19.35
ssh-keygen -R 193.233.232.48
ssh-keygen -R moderate-amethys.tailed4746.ts.net
```

---

## Помощь агента Cursor — когда и как

### Что агент **может**

| Ситуация | Как попросить |
|----------|---------------|
| Продолжить после обрыва | Переподключиться → **`продолжи`** |
| Починить VPS | «проверь SSH/Tailscale, apply_vps_ssh_stability» |
| Диагностика | «почему рвётся SSH» — смотрит journalctl |
| Добавить ключ | вставить содержимое `id_ed25519.pub` в чат |
| Долгий деплой | «запусти в tmux …» |

### Что агент **не может**

| Ситуация | Что делать вам |
|----------|----------------|
| Обрыв во время работы | Reload → `продолжи` (агент не переподключается сам) |
| Tailscale / `.ssh/config` на ПК | шаги 1–3 этого гайда |
| Keenetic / xray на роутере | использовать Tailscale |

### Алгоритм «починить с агентом»

```text
1. ssh empire-vps-ts hostname          ← должно работать
2. Cursor → empire-vps-ts → /root/projects/empire
3. В чате: «SSH рвался, проверь логи и apply_vps_ssh_stability»
4. Если SSH на ПК не работает — вставить вывод:
   ssh -vvv empire-vps-ts
   tailscale status
   (можно через empire-vps или телефон + Tailscale)
```

### Если агент недоступен (нет SSH)

1. Телефон + Tailscale → Termius → `root@100.84.19.35`
2. VNC хостера
3. `bash /root/projects/empire/scripts/apply_vps_ssh_stability.sh`
4. Cursor → `продолжи`

---

## Запасной путь без Tailscale

```powershell
ssh empire-vps
```

Cursor: `empire-vps`. **Ожидайте обрывы.** Долгие команды — только в tmux.

---

## Шпаргалка

**ПК:** `tailscale status` · `tailscale ping moderate-amethys` · `ssh empire-vps-ts hostname`

**VPS:** `tailscale status` · `journalctl -u ssh --since "30 min ago" | grep Accepted` · `bash scripts/apply_vps_ssh_stability.sh`

**Cursor:** F1 → Connect to Host → `empire-vps-ts` · Reload Window · Kill VS Code Server · чат: `продолжи`

---

## Связанные файлы

| Где | Файл |
|-----|------|
| **Этот файл (repo)** | `docs/cursor_vps_tailscale_ru.md` |
| Obsidian (vault) | `Life/tools/cursor_vps_tailscale_ru.md` |
| Краткая версия SSH | `docs/cursor_vps_ssh_ru.md` |
| SSH шаблон | `deploy/cursor_ssh_config_pc.example` |
| Настройка ПК (Tailscale) | `scripts/cursor_vps_tailscale_setup_pc.ps1` |
| Откат ПК | `scripts/cursor_vps_tailscale_rollback_pc.ps1` |
| VPS apply / rollback | `scripts/apply_vps_tailscale_ssh.sh` · `scripts/rollback_vps_tailscale_ssh.sh` |
| Двойной клик ПК | `scripts/install_cursor_tailscale_pc.bat` · `rollback_cursor_tailscale_pc.bat` |

---

## История (2026-06-20)

SSH шёл через xray (IP `79.139.217.172`); healthcheck перезапускал xray каждые 2 мин. Исправлено на VPS. На ПК — перейти на **`empire-vps-ts`** + SSH-ключ.

---

*Теги:* #empire #vps #cursor #tailscale #ssh #infra
