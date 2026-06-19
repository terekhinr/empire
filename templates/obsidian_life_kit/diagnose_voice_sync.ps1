# Voice sync diagnostic (PC). Run in PowerShell:
#   powershell -ExecutionPolicy Bypass -File "F:\YandexDisk\obsidian (2)\Life\tools\diagnose_voice_sync.ps1"

param(
    [string]$VaultPath = "F:\YandexDisk\obsidian (2)"
)

$ErrorActionPreference = "Continue"
$Raw = Join-Path $VaultPath "Life\voice\raw"

Write-Host "=== Voice sync diagnostic ===" -ForegroundColor Cyan
Write-Host ""

# 1. Vault path
Write-Host "[1] Yandex vault"
if (Test-Path -LiteralPath $VaultPath) {
    Write-Host "  OK: $VaultPath" -ForegroundColor Green
} else {
    Write-Host "  FAIL: vault not found: $VaultPath" -ForegroundColor Red
    Write-Host "  Fix -VaultPath or open correct Obsidian folder."
}

# 2. Google Drive / Easy Voice Recorder
Write-Host ""
Write-Host "[2] Google Drive -> Easy Voice Recorder"
$found = $null
$folderNames = @("Easy Voice Recorder", "EasyVoiceRecorder")
foreach ($drive in (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ge 0 })) {
    $root = $drive.Root
    if (-not (Test-Path -LiteralPath $root)) { continue }
    foreach ($top in Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue) {
        foreach ($name in $folderNames) {
            $candidate = Join-Path $top.FullName $name
            if (Test-Path -LiteralPath $candidate) {
                Write-Host "  Found: $candidate"
                $found = $candidate
            }
        }
    }
}
if (-not $found) {
    Write-Host "  FAIL: no Easy Voice Recorder on any drive letter." -ForegroundColor Red
    Write-Host "  Check: Google Drive for desktop is running and synced."
} else {
    $latest = Get-ChildItem -LiteralPath $found -Include *.mp3,*.m4a,*.wav -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 3
    if ($latest) {
        Write-Host "  Latest recordings on Google Drive (local mirror):"
        foreach ($f in $latest) {
            Write-Host ("    {0}  {1:yyyy-MM-dd HH:mm}" -f $f.Name, $f.LastWriteTime)
        }
    } else {
        Write-Host "  WARN: folder exists but no audio files." -ForegroundColor Yellow
    }
}

# 3. Life/voice/raw on Yandex
Write-Host ""
Write-Host "[3] Life/voice/raw (before upload to cloud)"
if (Test-Path -LiteralPath $Raw) {
    $rawLatest = Get-ChildItem -LiteralPath $Raw -Include *.mp3,*.m4a,*.wav -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 3
    if ($rawLatest) {
        foreach ($f in $rawLatest) {
            Write-Host ("  {0}  {1:yyyy-MM-dd HH:mm}" -f $f.Name, $f.LastWriteTime)
        }
    } else {
        Write-Host "  EMPTY - sync_evrec_to_life.ps1 never copied anything here." -ForegroundColor Yellow
    }
} else {
    Write-Host "  FAIL: $Raw does not exist" -ForegroundColor Red
}

# 4. Scheduled task
Write-Host ""
Write-Host "[4] Windows task Empire-Voice-Sync"
$task = schtasks /Query /TN "Empire-Voice-Sync" /FO LIST 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: task exists" -ForegroundColor Green
    $task | Select-String "Last Run Time|Next Run Time|Status" | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "  FAIL: task not installed." -ForegroundColor Red
    Write-Host "  Run: install_voice_sync_task.ps1"
}

# 5. Yandex Disk client
Write-Host ""
Write-Host "[5] Yandex Disk"
$yd = Get-Process -Name "YandexDisk*" -ErrorAction SilentlyContinue
if ($yd) {
    Write-Host "  OK: Yandex Disk process running" -ForegroundColor Green
} else {
    Write-Host "  WARN: Yandex Disk app may be closed - files stay local only." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Next steps ===" -ForegroundColor Cyan
Write-Host "1) Record 10 sec on phone -> wait 2 min -> re-run this script (step 2 date must be today)"
Write-Host "2) powershell -ExecutionPolicy Bypass -File sync_evrec_to_life.ps1"
Write-Host "3) Yandex Disk: wait for sync checkmark"
Write-Host "4) On disk.yandex.ru check: obsidian (2)/Life/voice/raw has new file"
Write-Host "5) VPS transcribes in ~15 min -> note in Входящие/ or say 'пенсия пост' for Empire/pension/inbox"
Write-Host ""
Write-Host "Bypass PC (recommended): VPS Google OAuth -> docs/voice_gdrive_oauth_ru.md"
Read-Host "Press Enter to close"
