# Easy Voice Recorder (Google Drive) -> Life/voice/raw (Yandex vault)
# ASCII-only for Windows PowerShell 5.1.
#
#   powershell -ExecutionPolicy Bypass -File "F:\YandexDisk\obsidian (2)\Life\tools\sync_evrec_to_life.ps1"
#   powershell -ExecutionPolicy Bypass -File "...\sync_evrec_to_life.ps1" -GoogleVoiceFolder "G:\My Drive\Easy Voice Recorder"

param(
    [string]$GoogleVoiceFolder = "",
    [string]$VaultPath = "F:\YandexDisk\obsidian (2)",
    [switch]$Transcribe
)

$ErrorActionPreference = "Stop"

function Find-EvrecFolder {
    if ($GoogleVoiceFolder -and (Test-Path -LiteralPath $GoogleVoiceFolder)) {
        return (Resolve-Path -LiteralPath $GoogleVoiceFolder).Path
    }

    $folderNames = @("Easy Voice Recorder", "EasyVoiceRecorder")
    $audioExt = @("*.mp3", "*.m4a", "*.aac", "*.wav")

    foreach ($drive in (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ge 0 })) {
        $root = $drive.Root
        if (-not (Test-Path -LiteralPath $root)) { continue }
        foreach ($top in Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue) {
            foreach ($name in $folderNames) {
                $candidate = Join-Path $top.FullName $name
                if (-not (Test-Path -LiteralPath $candidate)) { continue }
                foreach ($pattern in $audioExt) {
                    $hit = Get-ChildItem -LiteralPath $candidate -Filter $pattern -File -ErrorAction SilentlyContinue | Select-Object -First 1
                    if ($hit) { return (Resolve-Path -LiteralPath $candidate).Path }
                }
            }
        }
    }

    throw @"
Easy Voice Recorder folder not found on any drive.
1) Open Google Drive app -> note path to 'Easy Voice Recorder'
2) Run with explicit path:
   -GoogleVoiceFolder 'G:\My Drive\Easy Voice Recorder'
Or run: diagnose_voice_sync.ps1
"@
}

$src = Find-EvrecFolder
$Raw = Join-Path $VaultPath "Life\voice\raw"
$Tools = Join-Path $VaultPath "Life\tools"

Write-Host "From: $src"
Write-Host "To:   $Raw"

New-Item -ItemType Directory -Force -Path $Raw | Out-Null

$patterns = @("*.mp3", "*.m4a", "*.aac", "*.wav")
$copied = 0
foreach ($pattern in $patterns) {
    Get-ChildItem -LiteralPath $src -Filter $pattern -File -ErrorAction SilentlyContinue | ForEach-Object {
        $dest = Join-Path $Raw $_.Name
        if (-not (Test-Path -LiteralPath $dest)) {
            Copy-Item -LiteralPath $_.FullName -Destination $dest
            Write-Host ("Copied: " + $_.Name)
            $copied++
        }
    }
}

if ($copied -eq 0) {
    Write-Host "No new files (already in raw)."
} else {
    Write-Host ("Done: " + $copied + " file(s) -> " + $Raw)
    Write-Host "Wait for Yandex Disk sync (checkmark), then VPS transcribes in ~15 min."
}

if (-not $Transcribe) { exit 0 }

$py = Join-Path $Tools "voice_to_obsidian.py"
if (-not (Test-Path -LiteralPath $py)) {
    Write-Warning ("Missing: " + $py)
    exit 0
}

$venvPy = Join-Path $env:USERPROFILE ".venv-life\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPy)) {
    Write-Warning "Missing venv. Run:"
    Write-Warning "  python -m venv $env:USERPROFILE\.venv-life"
    Write-Warning "  .\.venv-life\Scripts\pip install faster-whisper watchdog"
    exit 0
}

& $venvPy $py --once
