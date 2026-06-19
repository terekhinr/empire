# Создаёт Life/ в Obsidian vault (задачи, голос, inbox).
# powershell -ExecutionPolicy Bypass -File scripts\setup_life_vault.ps1

param(
    [string]$VaultPath = "F:\YandexDisk\obsidian (2)"
)

$ErrorActionPreference = "Stop"
$Life = Join-Path $VaultPath "Life"

$dirs = @(
    "tasks\_import",
    "voice\raw",
    "voice\transcribed",
    "voice\processed",
    "inbox",
    "templates"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Life $d) | Out-Null
}

$readme = @"
# Life (личное)

Не синхронизируется на VPS. Только Яндекс.Диск + ПК + телефон.

- ``tasks/`` — TickTick → Obsidian Tasks
- ``voice/raw/`` — аудио с диктофона
- ``inbox/`` — расшифровки и черновики
- ``Empire/`` — посты в Telegram (отдельно)
"@
Set-Content -Path (Join-Path $Life "README.md") -Value $readme -Encoding UTF8

$dashboard = @'
# Задачи

## Просрочено
```tasks
not done
due before today
sort by due
```

## Сегодня
```tasks
not done
due today
```

## Следующие 7 дней
```tasks
not done
due after today
due before in 7 days
sort by due
```
'@
Set-Content -Path (Join-Path $Life "tasks\dashboard.md") -Value $dashboard -Encoding UTF8

$inbox = @"
# Inbox

## Без срока

"@
Set-Content -Path (Join-Path $Life "tasks\inbox.md") -Value $inbox -Encoding UTF8

Write-Host "OK: Life/ создан в $VaultPath"
Write-Host "  Откройте Life/tasks/dashboard.md в Obsidian"
Write-Host "  Включите плагин Tasks"
