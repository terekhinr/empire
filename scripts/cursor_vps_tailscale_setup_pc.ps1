# Empire: Tailscale + SSH for Cursor Remote (Windows PowerShell 5.1+)
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\cursor_vps_tailscale_setup_pc.ps1 -InstallTailscale

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
    @{ Alias = "empire-vps-ts"; HostName = $VpsHostTs }
    @{ Alias = "aeza-server"; HostName = $VpsHostTs }
    @{ Alias = "moderate-amethys"; HostName = $VpsHostDns }
    @{ Alias = "empire-vps"; HostName = $VpsHostPublic }
)

$MarkerBegin = "# BEGIN empire-tailscale-cursor"
$MarkerEnd = "# END empire-tailscale-cursor"
$KeyPath = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$ConfigPath = Join-Path $env:USERPROFILE ".ssh\config"
$BackupDir = Join-Path $env:USERPROFILE ".ssh\empire-backup"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}
function Write-Ok([string]$msg) {
    Write-Host "OK: $msg" -ForegroundColor Green
}
function Write-Warn([string]$msg) {
    Write-Host "WARN: $msg" -ForegroundColor Yellow
}

function Invoke-SshTest([string]$HostAlias) {
    $remoteTest = 'hostname; test -d /root/projects/empire && echo OK'
    $output = & ssh -o BatchMode=yes -o ConnectTimeout=15 $HostAlias $remoteTest 2>&1
    $code = $LASTEXITCODE
    return @{ Ok = ($code -eq 0 -and ($output -match "OK")); Output = ($output | Out-String).Trim() }
}

function Copy-KeyToVps([string]$TargetHost, [string]$PubKey) {
    $remoteCmd = "mkdir -p ~/.ssh; chmod 700 ~/.ssh; grep -qxF '$PubKey' ~/.ssh/authorized_keys 2>/dev/null || echo '$PubKey' >> ~/.ssh/authorized_keys; chmod 600 ~/.ssh/authorized_keys; echo KEY_OK"
    $output = & ssh -o ConnectTimeout=20 -o BatchMode=no "${VpsUser}@${TargetHost}" $remoteCmd 2>&1
    $code = $LASTEXITCODE
    return @{ Ok = ($code -eq 0 -and ($output -match "KEY_OK")); Output = ($output | Out-String).Trim() }
}

Write-Step "Empire: Tailscale + SSH for Cursor"

# --- Tailscale ---
$tsBin = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $tsBin) {
    if ($InstallTailscale) {
        Write-Warn "Tailscale not in PATH - installing via winget"
        & winget install --id Tailscale.Tailscale -e --accept-source-agreements --accept-package-agreements
        $tsBin = Get-Command tailscale -ErrorAction SilentlyContinue
    } else {
        Write-Warn "Install Tailscale: https://tailscale.com/download/windows"
        Write-Warn "Login with the same account as VPS, then re-run with -InstallTailscale"
    }
}

if ($tsBin) {
    $tsStatus = & tailscale status 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "tailscale status failed - open Tailscale from tray and login"
    } else {
        Write-Host $tsStatus
        if ($tsStatus -notmatch "100\.84\.19\.35|moderate-amethys") {
            Write-Warn "VPS moderate-amethys not in tailscale status"
        } else {
            Write-Ok "VPS visible in tailnet"
        }
        & tailscale ping -c 1 $VpsHostTs 2>&1 | ForEach-Object { Write-Host $_ }
    }
}

# --- SSH dir + key ---
$sshDir = Join-Path $env:USERPROFILE ".ssh"
if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
}

if (-not (Test-Path $KeyPath)) {
    Write-Warn "Creating key $KeyPath"
    & ssh-keygen -t ed25519 -C "cursor-pc-empire" -f $KeyPath -N '""'
} else {
    Write-Ok "Key exists: $KeyPath"
}

# --- Backup config ---
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if (Test-Path $ConfigPath) {
    Copy-Item $ConfigPath (Join-Path $BackupDir "config.$stamp.bak") -Force
    Write-Ok "Backup: $BackupDir\config.$stamp.bak"
} else {
    New-Item -ItemType File -Path $ConfigPath -Force | Out-Null
}

# --- Build SSH block ---
$hostLines = New-Object System.Collections.Generic.List[string]
[void]$hostLines.Add($MarkerBegin)
[void]$hostLines.Add("# Empire Cursor Tailscale - rollback: cursor_vps_tailscale_rollback_pc.ps1")
foreach ($h in $HostsToConfigure) {
    [void]$hostLines.Add("")
    [void]$hostLines.Add("Host $($h.Alias)")
    [void]$hostLines.Add("    HostName $($h.HostName)")
    [void]$hostLines.Add("    User $VpsUser")
    [void]$hostLines.Add("    IdentityFile ~/.ssh/id_ed25519")
    [void]$hostLines.Add("    ServerAliveInterval 30")
    [void]$hostLines.Add("    ServerAliveCountMax 20")
    [void]$hostLines.Add("    TCPKeepAlive yes")
    [void]$hostLines.Add("    ConnectTimeout 60")
}
[void]$hostLines.Add($MarkerEnd)
$newBlock = ($hostLines -join [Environment]::NewLine) + [Environment]::NewLine

$configText = ""
if (Test-Path $ConfigPath) {
    $configText = Get-Content -Raw -LiteralPath $ConfigPath
}
if ($null -eq $configText) { $configText = "" }

if ($configText -match [regex]::Escape($MarkerBegin)) {
    $pattern = "(?s)$([regex]::Escape($MarkerBegin)).*?$([regex]::Escape($MarkerEnd))\r?\n?"
    $configText = [regex]::Replace($configText, $pattern, $newBlock)
    Write-Ok "Updated SSH block in config"
} else {
    if ($configText.Length -gt 0 -and -not $configText.EndsWith("`n")) {
        $configText += [Environment]::NewLine
    }
    $configText += [Environment]::NewLine + $newBlock
    Write-Ok "Added SSH block to config"
}

$removeOld = "# [removed by empire-tailscale-setup] old Host aeza-server - see block $MarkerBegin" + [Environment]::NewLine
$configText = [regex]::Replace(
    $configText,
    "(?ms)^Host aeza-server\r?\n(?!# BEGIN)(?:^[ \t].*\r?\n)*",
    $removeOld
)

$utf8Bom = New-Object System.Text.UTF8Encoding $true
[System.IO.File]::WriteAllText($ConfigPath, $configText.TrimEnd() + [Environment]::NewLine, $utf8Bom)

# --- Copy pubkey ---
if (-not $SkipKeyCopy) {
    $pub = (Get-Content -LiteralPath "${KeyPath}.pub" -Raw).Trim()
    $doCopy = $NonInteractive
    if (-not $NonInteractive) {
        $ans = Read-Host "Copy SSH key to VPS via Tailscale ${VpsUser}@${VpsHostTs}? (Y/n)"
        $doCopy = ($ans -eq "" -or $ans -match "^[Yy]")
    }

    if ($doCopy) {
        Write-Step "Copy key via Tailscale $VpsHostTs"
        $result = Copy-KeyToVps $VpsHostTs $pub
        if (-not $result.Ok) {
            Write-Warn "Tailscale failed: $($result.Output)"
            Write-Warn "Trying public IP $VpsHostPublic"
            $result = Copy-KeyToVps $VpsHostPublic $pub
            if (-not $result.Ok) {
                Write-Warn "Auto copy failed. Add this key on VPS manually:"
                Get-Content -LiteralPath "${KeyPath}.pub"
            } else {
                Write-Ok "Key on VPS (public IP)"
            }
        } else {
            Write-Ok "Key on VPS (Tailscale)"
        }
    }
}

# --- Test ---
Write-Step "SSH test"
$testOk = $false
foreach ($alias in @("empire-vps-ts", "aeza-server")) {
    Write-Host "ssh $alias ..."
    $t = Invoke-SshTest $alias
    if ($t.Ok) {
        Write-Ok "$alias -> $($t.Output)"
        $testOk = $true
        break
    } else {
        Write-Warn "$alias failed: $($t.Output)"
    }
}

Write-Step "Done"
Write-Host ""
Write-Host "Cursor: F1 -> Remote-SSH: Connect to Host -> empire-vps-ts" -ForegroundColor Green
Write-Host "Open Folder: $EmpirePathRemote" -ForegroundColor Green
Write-Host "Rollback: $ScriptDir\OTKAT.bat" -ForegroundColor Green
Write-Host ""

if (-not $testOk) {
    Write-Warn "SSH test failed - check Tailscale tray and run this script again"
    exit 1
}
