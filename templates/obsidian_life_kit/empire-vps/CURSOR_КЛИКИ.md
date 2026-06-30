# Empire VPS — что нажимать в Cursor

Папка на ПК:

```text
F:\YandexDisk\obsidian (2)\Life\tools\empire-vps\
```

---

## Установка (один раз)

1. Яндекс.Диск — sync
2. Двойной клик **`УСТАНОВИТЬ_TAILSCALE.bat`**
3. Tailscale в трее — **Connected**

---

## Cursor — нормальное подключение

1. Запустить **Cursor** на Windows
2. **`Connect via SSH`** *(или F1 → Remote-SSH: Connect to Host...)*
3. Клик **`empire-vps-ts`** *(или `aeza-server`)*
4. Platform → **Linux**
5. **`File` → `Open Folder...`**
6. Путь: **`/root/projects/empire`**
7. Trust → **Yes**

Низ слева: **`SSH: empire-vps-ts`**

---

## Если не получилось

См. **`CURSOR_КЛИКИ.md`** в этой папке (полная цепочка A→G).

Коротко:

1. Ещё раз **`УСТАНОВИТЬ_TAILSCALE.bat`**
2. PowerShell: `ssh empire-vps-ts hostname` — должно работать без пароля
3. F1 → **Kill VS Code Server on Host** → `empire-vps-ts`
4. F1 → **Connect to Host...** → `empire-vps-ts`
5. F1 → **Show Log** — скопировать ошибку агенту
6. Запасной: Connect to Host → **`empire-vps`**

---

## Откат

1. **Закрыть Cursor**
2. Двойной клик **`ОТКАТ.bat`**
3. Cursor → Connect to Host → **старый хост** (`aeza-server` / `empire-vps`)

Полный откат config:

```powershell
powershell -ExecutionPolicy Bypass -File .\cursor_vps_tailscale_rollback_pc.ps1 -RestoreLatestBackup
```

---

Полный техгайд: на VPS `docs/cursor_vps_tailscale_ru.md` и `docs/cursor_vps_tailscale_clicks_ru.md`
