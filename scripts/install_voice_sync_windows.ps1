# DEPRECATED: use install_voice_rclone_nightly_windows.ps1 (once per night, hidden).
# Empire: Google Drive -> Yandex Life/voice/raw (zadacha Windows)
# powershell -ExecutionPolicy Bypass -File install_voice_sync_task.ps1

param(
    [string]$GoogleVoiceFolder = "G:\Мой диск\Easy Voice Recorder",
    [string]$VaultPath = "F:\YandexDisk\obsidian (2)",
    [string]$TaskName = "Empire-Voice-Sync",
    [int]$IntervalMinutes = 15
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SyncScript = Join-Path $ScriptDir "sync_evrec_to_life.ps1"

if (-not (Test-Path $SyncScript)) {
    Write-Error "Net skripta: $SyncScript"
}

$psArgs = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -GoogleVoiceFolder "{1}" -VaultPath "{2}"' -f $SyncScript, $GoogleVoiceFolder, $VaultPath
$taskCmd = "powershell.exe $psArgs"

schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
$result = schtasks /Create /TN $TaskName /TR $taskCmd /SC MINUTE /MO $IntervalMinutes /F 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "schtasks ne sozdal zadachu: $result"
}

Write-Host "OK: zadacha $TaskName kazhdye $IntervalMinutes min."
Write-Host "Proverka: schtasks /Query /TN $TaskName"
Write-Host "Ruchno: powershell -ExecutionPolicy Bypass -File $SyncScript"
