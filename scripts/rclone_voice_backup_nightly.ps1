# Nightly backup: Easy Voice Recorder -> Yandex Life/voice/raw (duplicates only).
# VPS transcribes from Google Drive directly; this is a PC-side archive copy.
#
#   powershell -ExecutionPolicy Bypass -File scripts\rclone_voice_backup_nightly.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\rclone_voice_backup_nightly.ps1 -DryRun

param(
    [string]$GdriveRemote = "gdrive",
    [string]$GdrivePath = "Easy Voice Recorder",
    [string]$YandexRemote = "yandex",
    [string]$YandexDest = "obsidian (2)/Life/voice/raw",
    [string]$LocalGdriveFolder = "",
    [string]$LogDir = "$env:USERPROFILE\empire-logs",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Log([string]$Msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
    Write-Host $line
    if ($script:LogFile) {
        Add-Content -LiteralPath $script:LogFile -Value $line -Encoding UTF8
    }
}

function Test-RcloneRemote([string]$Name) {
    $list = & rclone listremotes 2>$null
    return ($list -match ("^{0}:$" -f [regex]::Escape($Name)))
}

function Find-LocalEvrec {
    param([string]$Explicit)
    if ($Explicit -and (Test-Path -LiteralPath $Explicit)) {
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    $names = @("Easy Voice Recorder", "EasyVoiceRecorder")
    foreach ($drive in (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ge 0 })) {
        foreach ($top in (Get-ChildItem -LiteralPath $drive.Root -Directory -ErrorAction SilentlyContinue)) {
            foreach ($n in $names) {
                $c = Join-Path $top.FullName $n
                if (Test-Path -LiteralPath $c) { return (Resolve-Path -LiteralPath $c).Path }
            }
        }
    }
    return $null
}

if (-not (Get-Command rclone -ErrorAction SilentlyContinue)) {
    throw "rclone not found. Install: winget install Rclone.Rclone"
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$script:LogFile = Join-Path $LogDir ("voice-rclone-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

$include = @(
    "--include", "*.mp3",
    "--include", "*.m4a",
    "--include", "*.aac",
    "--include", "*.wav"
)
$common = @(
    "--fast-list",
    "--ignore-existing",
    "--transfers", "2",
    "--timeout", "30m",
    "-v"
)
if ($DryRun) { $common += "--dry-run" }

$dest = "{0}:{1}" -f $YandexRemote, $YandexDest
if (-not (Test-RcloneRemote $YandexRemote)) {
    throw "Remote '$YandexRemote' not configured. Run: rclone config"
}

$src = $null
$mode = ""

if (Test-RcloneRemote $GdriveRemote) {
    $src = "{0}:{1}" -f $GdriveRemote, $GdrivePath
    $mode = "cloud"
} else {
    $local = Find-LocalEvrec -Explicit $LocalGdriveFolder
    if ($local) {
        $src = $local
        $mode = "local-gdrive-folder"
    }
}

if (-not $src) {
    throw @"
No source found.
Configure rclone remote '$GdriveRemote' OR set -LocalGdriveFolder to Google Drive sync path.
"@
}

Write-Log "START mode=$mode src=$src dest=$dest"
& rclone copy $src $dest @common @include
if ($LASTEXITCODE -ne 0) {
    Write-Log "FAIL exit=$LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Log "DONE"
