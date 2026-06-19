# Один раз на ПК: SSH-ключ + фрагмент config для Cursor Remote SSH → VPS Empire.
#
# PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\cursor_vps_ssh_setup_pc.ps1
#
# Пароль root спросит один раз при копировании ключа на VPS.

$ErrorActionPreference = "Stop"
$VpsHost = "193.233.232.48"
$VpsUser = "root"
$SshAlias = "empire-vps"
$KeyPath = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$ConfigPath = Join-Path $env:USERPROFILE ".ssh\config"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== Cursor / VPS SSH setup (Empire) ===" -ForegroundColor Cyan

$sshDir = Join-Path $env:USERPROFILE ".ssh"
if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
}

if (-not (Test-Path $KeyPath)) {
    Write-Host "Создаём ключ: $KeyPath" -ForegroundColor Yellow
    ssh-keygen -t ed25519 -C "cursor-pc-empire" -f $KeyPath -N '""'
} else {
    Write-Host "Ключ уже есть: $KeyPath" -ForegroundColor Green
}

$block = @"

# --- empire-vps (Cursor Remote SSH) ---
Host $SshAlias
    HostName $VpsHost
    User $VpsUser
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 30
    ServerAliveCountMax 6
    TCPKeepAlive yes
"@

$configText = ""
if (Test-Path $ConfigPath) {
    $configText = Get-Content -Raw $ConfigPath
}

if ($configText -match "Host\s+$SshAlias\b") {
    Write-Host "Блок Host $SshAlias уже в $ConfigPath" -ForegroundColor Green
} else {
    Add-Content -Path $ConfigPath -Value $block
    Write-Host "Добавлен Host $SshAlias в $ConfigPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Публичный ключ (на VPS в authorized_keys) ===" -ForegroundColor Cyan
Get-Content "${KeyPath}.pub"
Write-Host ""

$copy = Read-Host "Скопировать ключ на ${VpsUser}@${VpsHost}? (Y/n)"
if ($copy -eq "" -or $copy -match "^[Yy]") {
    $pub = Get-Content "${KeyPath}.pub" -Raw
    ssh "${VpsUser}@${VpsHost}" "mkdir -p ~/.ssh && chmod 700 ~/.ssh && grep -qxF '$($pub.Trim())' ~/.ssh/authorized_keys 2>/dev/null || echo '$($pub.Trim())' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Не удалось скопировать ключ. Сделайте вручную — см. docs/cursor_vps_ssh_ru.md"
        exit 1
    }
    Write-Host "Ключ на VPS." -ForegroundColor Green
}

Write-Host ""
Write-Host "Проверка: ssh $SshAlias hostname" -ForegroundColor Cyan
ssh $SshAlias "hostname && test -d /root/projects/empire && echo OK: /root/projects/empire"

Write-Host ""
Write-Host "Cursor: Remote-SSH -> Connect to Host -> $SshAlias" -ForegroundColor Green
Write-Host "Док: $RepoRoot\docs\cursor_vps_ssh_ru.md" -ForegroundColor Green
