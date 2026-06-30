# Настройка Cursor Remote SSH через Tailscale (Windows).
# Запуск (из F:\Media Empire или любого клона):
#   powershell -ExecutionPolicy Bypass -File scripts\cursor_vps_tailscale_setup_pc.ps1
#
# Опции:
#   -InstallTailscale   установить Tailscale через winget (если нет)
#   -SkipKeyCopy        только config, без копирования ключа на VPS
#   -NonInteractive     без Read-Host (ключ копируется автоматически)

param(
    [switch]$InstallTailscale,
    [switch]$SkipKeyCopy,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"

$VpsHostPublic = "193.233.232.48"
$VpsHostTs = "100.84.19.35"
$VpsHostDns = "moderate-amethys.tailed4746.ts.net"
$VpsUser = "root"
$EmpirePathRemote = "/root/projects/empire"

$HostsToConfigure = @(
    @{ Alias = "empire-vps-ts"; HostName = $VpsHostTs; Primary = $true }
    @{ Alias = "aeza-server";   HostName = $VpsHostTs; Primary = $false }
    @{ Alias = "moderate-amethys"; HostName = $VpsHostDns; Primary = $false }
    @{ Alias = "empire-vps";    HostName = $VpsHostPublic; Primary = $false }
)

$MarkerBegin = "# BEGIN empire-tailscale-cursor"
$MarkerEnd = "# END empire-tailscale-cursor"
$KeyPath = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$ConfigPath = Join-Path $env:USERPROFILE ".ssh\config"
$BackupDir = Join-Path $env:USERPROFILE ".ssh\empire-backup"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Write-Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "WARN: $msg" -ForegroundColor Yellow }

Write-Step "Empire: Tailscale + SSH для Cursor"

# --- Tailscale ---
$tsBin = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $tsBin) {
    if ($InstallTailscale) {
        Write-Warn "Tailscale не найден — winget install"
        winget install --id Tailscale.Tailscale -e --accept-source-agreements --accept-package-agreements
        $tsBin = Get-Command tailscale -ErrorAction SilentlyContinue
    } else {
        Write-Warn @"
Tailscale CLI не в PATH.
  1) Установите: https://tailscale.com/download/windows
  2) Войдите в аккаунт potertiy@… (тот же, что на VPS)
  3) Повторите с -InstallTailscale или после установки
"@
    }
}

if ($tsBin) {
    $tsStatus = & tailscale status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "tailscale status failed — откройте Tailscale из трея и войдите в аккаунт"
    } else {
        Write-Host $tsStatus
        if ($tsStatus -notmatch "100\.84\.19\.35|moderate-amethys") {
            Write-Warn "VPS moderate-amethys не виден в tailscale status"
        } else {
            Write-Ok "VPS в tailnet"
        }
        & tailscale ping -c 1 $VpsHostTs 2>&1 | ForEach-Object { Write-Host $_ }
    }
}

# --- SSH dir + key ---
$sshDir = Join-Path $env:USERPROFILE ".ssh"
if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir -Force | Out-Null }

if (-not (Test-Path $KeyPath)) {
    Write-Warn "Создаём ключ $KeyPath"
    ssh-keygen -t ed25519 -C "cursor-pc-empire" -f $KeyPath -N '""'
} else {
    Write-Ok "Ключ: $KeyPath"
}

# --- Backup config ---
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if (Test-Path $ConfigPath) {
    Copy-Item $ConfigPath (Join-Path $BackupDir "config.$stamp.bak") -Force
    Write-Ok "Бэкап config -> $BackupDir\config.$stamp.bak"
} else {
    New-Item -ItemType File -Path $ConfigPath -Force | Out-Null
}

# --- Build SSH block ---
$hostLines = @($MarkerBegin, "# Empire Cursor — Tailscale (rollback: cursor_vps_tailscale_rollback_pc.ps1)")
foreach ($h in $HostsToConfigure) {
    $hostLines += ""
    $hostLines += "Host $($h.Alias)"
    $hostLines += "    HostName $($h.HostName)"
    $hostLines += "    User $VpsUser"
    $hostLines += "    IdentityFile ~/.ssh/id_ed25519"
    $hostLines += "    ServerAliveInterval 30"
    $hostLines += "    ServerAliveCountMax 20"
    $hostLines += "    TCPKeepAlive yes"
    $hostLines += "    ConnectTimeout 60"
}
$hostLines += $MarkerEnd
$newBlock = ($hostLines -join "`n") + "`n"

$configText = Get-Content -Raw $ConfigPath -ErrorAction SilentlyContinue
if (-not $configText) { $configText = "" }

if ($configText -match [regex]::Escape($MarkerBegin)) {
    $pattern = "(?s)$([regex]::Escape($MarkerBegin)).*?$([regex]::Escape($MarkerEnd))\r?\n?"
    $configText = [regex]::Replace($configText, $pattern, $newBlock)
    Write-Ok "Обновлён блок $MarkerBegin в config"
} else {
    if (-not $configText.EndsWith("`n")) { $configText += "`n" }
    $configText += "`n$newBlock"
    Write-Ok "Добавлен блок $MarkerBegin в config"
}

# Убрать старый aeza-server вне маркера (часто ведёт на публичный IP)
$configText = [regex]::Replace(
    $configText,
    "(?ms)^Host aeza-server\r?\n(?!# BEGIN)(?:^[ \t].*\r?\n)*",
    "# [removed by empire-tailscale-setup] old Host aeza-server — см. блок $MarkerBegin`n"
)

Set-Content -Path $ConfigPath -Value $configText.TrimEnd() + "`n" -NoNewline:$false -Encoding utf8

# --- Copy pubkey to VPS (Tailscale first, then public IP) ---
if (-not $SkipKeyCopy) {
    $pub = (Get-Content "${KeyPath}.pub" -Raw).Trim()
    $remoteCmd = @"
mkdir -p ~/.ssh && chmod 700 ~/.ssh &&
grep -qxF '$pub' ~/.ssh/authorized_keys 2>/dev/null || echo '$pub' >> ~/.ssh/authorized_keys &&
chmod 600 ~/.ssh/authorized_keys && echo KEY_OK
"@

    $doCopy = $NonInteractive
    if (-not $NonInteractive) {
        $ans = Read-Host "Скопировать SSH-ключ на VPS через Tailscale ($VpsUser@${VpsHostTs})? (Y/n)"
        $doCopy = ($ans -eq "" -or $ans -match "^[Yy]")
    }

    if ($doCopy) {
        Write-Step "Копирование ключа (Tailscale $VpsHostTs)"
        $out = ssh -o ConnectTimeout=15 -o BatchMode=no "${VpsUser}@${VpsHostTs}" $remoteCmd 2>&1
        if ($LASTEXITCODE -ne 0 -or $out -notmatch "KEY_OK") {
            Write-Warn "Tailscale не прошёл — пробуем публичный IP $VpsHostPublic"
            $out = ssh -o ConnectTimeout=20 "${VpsUser}@${VpsHostPublic}" $remoteCmd 2>&1
            if ($LASTEXITCODE -ne 0 -or $out -notmatch "KEY_OK") {
                Write-Warn "Не удалось скопировать ключ автоматически. Вставьте вручную на VPS:"
                Get-Content "${KeyPath}.pub"
            } else {
                Write-Ok "Ключ на VPS (через публичный IP)"
            }
        } else {
            Write-Ok "Ключ на VPS (через Tailscale)"
        }
    }
}

# --- Test ---
Write-Step "Проверка SSH"
$testOk = $false
foreach ($alias in @("empire-vps-ts", "aeza-server")) {
    Write-Host "ssh $alias ..."
    $r = ssh -o BatchMode=yes -o ConnectTimeout=15 $alias "hostname && test -d $EmpirePathRemote && echo OK" 2>&1
    if ($LASTEXITCODE -eq 0 -and $r -match "OK") {
        Write-Ok "$alias -> $r"
        $testOk = $true
        break
    } else {
        Write-Warn "$alias failed: $r"
    }
}

Write-Step "Готово"
Write-Host @"

Cursor:
  F1 -> Remote-SSH: Connect to Host -> empire-vps-ts
  (или aeza-server — теперь тоже через Tailscale)
  Open Folder: $EmpirePathRemote

Откат на ПК:
  powershell -ExecutionPolicy Bypass -File scripts\cursor_vps_tailscale_rollback_pc.ps1

Док: $RepoRoot\docs\cursor_vps_tailscale_ru.md
"@ -ForegroundColor Green

if (-not $testOk) {
    Write-Warn "SSH-тест не прошёл — проверьте Tailscale в трее и повторите скрипт"
    exit 1
}
