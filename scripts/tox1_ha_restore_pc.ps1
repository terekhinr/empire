# TOX1: с ПК — починить дополнения + восстановить бэкап HA (уже лежит в /usr/share/hassio/backup/).
#
# PowerShell (от имени пользователя Destroy):
#   cd "F:\YandexDisk\obsidian (2)\Life\tools"
#   powershell -ExecutionPolicy Bypass -File tox1_ha_restore_pc.ps1
#
# Нужен OpenSSH (scp/ssh) — как при загрузке бэкапа. Пароль root спросит 1–2 раза.

$HostIP = "192.168.1.41"
$User   = "root"
$ScriptDir = $PSScriptRoot
$RemoteScript = Join-Path $ScriptDir "tox1_ha_restore_all.sh"

if (-not (Test-Path $RemoteScript)) {
    Write-Error "Нет файла: $RemoteScript"
    exit 1
}

Write-Host "=== Копируем скрипт на $HostIP ===" -ForegroundColor Cyan
scp $RemoteScript "${User}@${HostIP}:/root/tox1_ha_restore_all.sh"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Восстановление slug 204bd3e1 (10–15 мин, не закрывайте окно) ===" -ForegroundColor Cyan
ssh "${User}@${HostIP}" "ha backups restore 204bd3e1"

Write-Host ""
Write-Host "Если всё OK — откройте http://${HostIP}:8123 через несколько минут." -ForegroundColor Green
