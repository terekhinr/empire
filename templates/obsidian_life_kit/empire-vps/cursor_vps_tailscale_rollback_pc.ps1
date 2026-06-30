# Откат cursor_vps_tailscale_setup_pc.ps1 на Windows.
#   powershell -ExecutionPolicy Bypass -File scripts\cursor_vps_tailscale_rollback_pc.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\cursor_vps_tailscale_rollback_pc.ps1 -RestoreLatestBackup

param(
    [switch]$RestoreLatestBackup
)

$ErrorActionPreference = "Stop"
$MarkerBegin = "# BEGIN empire-tailscale-cursor"
$MarkerEnd = "# END empire-tailscale-cursor"
$ConfigPath = Join-Path $env:USERPROFILE ".ssh\config"
$BackupDir = Join-Path $env:USERPROFILE ".ssh\empire-backup"

Write-Host "=== Empire: откат Tailscale SSH config ===" -ForegroundColor Cyan

if ($RestoreLatestBackup) {
    $latest = Get-ChildItem "$BackupDir\config.*.bak" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        Write-Error "Нет бэкапов в $BackupDir"
        exit 1
    }
    Copy-Item $latest.FullName $ConfigPath -Force
    Write-Host "OK: восстановлен $($latest.Name)" -ForegroundColor Green
    exit 0
}

if (-not (Test-Path $ConfigPath)) {
    Write-Host "OK: config не существует, нечего откатывать" -ForegroundColor Green
    exit 0
}

$configText = Get-Content -Raw $ConfigPath
if ($configText -notmatch [regex]::Escape($MarkerBegin)) {
    Write-Host "WARN: маркер $MarkerBegin не найден — откат только через -RestoreLatestBackup" -ForegroundColor Yellow
    $latest = Get-ChildItem "$BackupDir\config.*.bak" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) {
        Write-Host "Последний бэкап: $($latest.FullName)"
        Write-Host "Запустите: ... -RestoreLatestBackup"
    }
    exit 1
}

$pattern = "(?s)\r?\n?$([regex]::Escape($MarkerBegin)).*?$([regex]::Escape($MarkerEnd))\r?\n?"
$newText = [regex]::Replace($configText, $pattern, "`n")
Set-Content -Path $ConfigPath -Value $newText.TrimEnd() + "`n" -Encoding utf8

Write-Host "OK: удалён блок $MarkerBegin .. $MarkerEnd" -ForegroundColor Green
Write-Host "Cursor снова используйте старый хост (empire-vps / aeza-server как было до setup)." -ForegroundColor Yellow
Write-Host "Полный откат config: -RestoreLatestBackup" -ForegroundColor Yellow
