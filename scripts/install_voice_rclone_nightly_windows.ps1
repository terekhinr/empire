# Empire: nightly rclone voice backup (replaces 15-min Empire-Voice-Sync flash).
#
#   powershell -ExecutionPolicy Bypass -File scripts\install_voice_rclone_nightly_windows.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\install_voice_rclone_nightly_windows.ps1 -Hour 3 -Minute 15

param(
    [string]$TaskName = "Empire-Voice-Rclone-Nightly",
    [string]$OldTaskName = "Empire-Voice-Sync",
    [int]$Hour = 3,
    [int]$Minute = 0,
    [string]$GdriveRemote = "gdrive",
    [string]$YandexRemote = "yandex",
    [string]$LocalGdriveFolder = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackupScript = Join-Path $ScriptDir "rclone_voice_backup_nightly.ps1"

if (-not (Test-Path -LiteralPath $BackupScript)) {
    Write-Error "Missing: $BackupScript"
}

# Remove old 15-minute task if present (stops desktop flashing).
schtasks /Delete /TN $OldTaskName /F 2>$null | Out-Null
Write-Host "Removed old task (if existed): $OldTaskName"

$extra = ""
if ($LocalGdriveFolder) {
    $extra = ' -LocalGdriveFolder "' + $LocalGdriveFolder + '"'
}
$psArgs = (
    '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -GdriveRemote "{1}" -YandexRemote "{2}"{3}' -f
    $BackupScript, $GdriveRemote, $YandexRemote, $extra
)
$taskCmd = "powershell.exe $psArgs"
$time = "{0:D2}:{1:D2}" -f $Hour, $Minute

schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
$result = schtasks /Create /TN $TaskName /TR $taskCmd /SC DAILY /ST $time /F 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "schtasks failed: $result"
}

Write-Host "OK: $TaskName daily at $time (hidden window)."
Write-Host "Manual test: powershell -ExecutionPolicy Bypass -File $BackupScript -DryRun"
Write-Host "Logs: $env:USERPROFILE\empire-logs\voice-rclone-*.log"
Write-Host "Check: schtasks /Query /TN $TaskName /V /FO LIST"
