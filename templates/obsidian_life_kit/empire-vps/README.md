# Empire VPS — Tailscale + Cursor (Windows)

Папка на ПК (Яндекс.Диск):

```text
F:\YandexDisk\obsidian (2)\Life\tools\empire-vps\
```

**Репозиторий Empire на ПК не нужен.** `F:\Media Empire` — только workspace Obsidian, не git-клон.

---

## Установка (один раз)

1. Дождитесь синка Яндекс.Диска (или **Sync** в трее).
2. Двойной клик: **`УСТАНОВИТЬ_TAILSCALE.bat`**
3. Tailscale — войти в аккаунт `potertiy@…` (тот же, что на VPS).
4. При запросе — скопировать SSH-ключ на VPS (пароль root последний раз).

Или PowerShell:

```powershell
cd "F:\YandexDisk\obsidian (2)\Life\tools\empire-vps"
powershell -ExecutionPolicy Bypass -File .\cursor_vps_tailscale_setup_pc.ps1 -InstallTailscale
```

---

## Cursor после установки

`F1` → **Remote-SSH: Connect to Host** → **`empire-vps-ts`** или **`aeza-server`**

Open Folder: `/root/projects/empire`

---

## Откат

Двойной клик: **`ОТКАТ.bat`**

Полный откат `~\.ssh\config` из бэкапа:

```powershell
powershell -ExecutionPolicy Bypass -File .\cursor_vps_tailscale_rollback_pc.ps1 -RestoreLatestBackup
```

---

## Файлы

| Файл | Назначение |
|------|------------|
| `УСТАНОВИТЬ_TAILSCALE.bat` | Запуск setup |
| `ОТКАТ.bat` | Убрать блок Tailscale из SSH config |
| `cursor_vps_tailscale_setup_pc.ps1` | Основной скрипт |
| `cursor_vps_tailscale_rollback_pc.ps1` | Откат |

Бэкапы SSH config: `%USERPROFILE%\.ssh\empire-backup\`

---

## VPS (уже настроено агентом)

```bash
bash /root/projects/empire/scripts/apply_vps_tailscale_ssh.sh
```

Откат на VPS:

```bash
bash /root/projects/empire/scripts/rollback_vps_tailscale_ssh.sh
```

Полный гайд на VPS: `docs/cursor_vps_tailscale_ru.md`

---

*Синк: VPS → Яндекс.Диск через rclone (`Life/tools/empire-vps/`)*
