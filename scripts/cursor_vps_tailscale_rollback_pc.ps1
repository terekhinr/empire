# Rollback cursor_vps_tailscale_setup_pc.ps1 (Windows PowerShell 5.1+)

param(
    [switch]$RestoreLatestBackup
)

$ErrorActionPreference = "Stop"
$MarkerBegin = "# BEGIN empire-tailscale-cursor"
$MarkerEnd = "# END empire-tailscale-cursor"
$ConfigPath = Join-Path $env:USERPROFILE ".ssh\config"
$BackupDir = Join-Path $env:USERPROFILE ".ssh\empire-backup"

Write-Host "=== Empire: rollback Tailscale SSH config ===" -ForegroundColor Cyan

if ($RestoreLatestBackup) {
    $latest = Get-ChildItem "$BackupDir\config.*.bak" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        Write-Error "No backups in $BackupDir"
        exit 1
    }
    Copy-Item $latest.FullName $ConfigPath -Force
    Write-Host "OK: restored $($latest.Name)" -ForegroundColor Green
    exit 0
}

if (-not (Test-Path $ConfigPath)) {
    Write-Host "OK: no config file" -ForegroundColor Green
    exit 0
}

$configText = Get-Content -Raw -LiteralPath $ConfigPath
if ($configText -notmatch [regex]::Escape($MarkerBegin)) {
    Write-Host "WARN: marker not found - use -RestoreLatestBackup" -ForegroundColor Yellow
    $latest = Get-ChildItem "$BackupDir\config.*.bak" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($latest) {
        Write-Host "Latest backup: $($latest.FullName)"
        Write-Host "Run: powershell -File .\cursor_vps_tailscale_rollback_pc.ps1 -RestoreLatestBackup"
    }
    exit 1
}

$pattern = "(?s)\r?\n?$([regex]::Escape($MarkerBegin)).*?$([regex]::Escape($MarkerEnd))\r?\n?"
$newText = [regex]::Replace($configText, $pattern, [Environment]::NewLine)
$utf8Bom = New-Object System.Text.UTF8Encoding $true
[System.IO.File]::WriteAllText($ConfigPath, $newText.TrimEnd() + [Environment]::NewLine, $utf8Bom)

Write-Host "OK: removed block $MarkerBegin .. $MarkerEnd" -ForegroundColor Green
Write-Host "Use old SSH host in Cursor (aeza-server / empire-vps as before)." -ForegroundColor Yellow
