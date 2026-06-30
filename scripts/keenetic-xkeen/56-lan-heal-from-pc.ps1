# С ПК в LAN (192.168.1.x). PowerShell от админа:
#   irm http://193.233.232.48:8787/56-lan-heal-from-pc.ps1 | iex
$ErrorActionPreference = 'Stop'
$router = '192.168.1.1'
$port = 222
$pass = 'keenetic'
$base = 'http://193.233.232.48:8787'

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
  Write-Host 'Установите OpenSSH Client (Параметры -> Приложения -> Дополнительные компоненты)'
  exit 1
}

$ping = Test-Connection -ComputerName $router -Count 1 -Quiet
if (-not $ping) {
  Write-Host "Роутер $router недоступен по ping"
  exit 1
}

$cmd = "curl -fsSL $base/55-minimal-nfqws2.sh | sh"
Write-Host "Запуск heal на роутере..."
$env:SSHPASS = $pass
if (Get-Command sshpass -ErrorAction SilentlyContinue) {
  sshpass -e ssh -o StrictHostKeyChecking=no -p $port root@$router $cmd
} else {
  Write-Host "Пароль: keenetic"
  ssh -o StrictHostKeyChecking=no -p $port root@$router $cmd
}
Write-Host 'Готово. Проверьте YouTube в инкогнито.'
