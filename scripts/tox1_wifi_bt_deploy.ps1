# С ПК: поставить WiFi/BT на TOX1 (нужен пароль root на боксе).
# powershell -ExecutionPolicy Bypass -File tox1_wifi_bt_deploy.ps1

$HostIP = "100.80.133.85"
$Script = Join-Path $PSScriptRoot "tox1_wifi_bt_install.sh"
scp $Script "root@${HostIP}:/root/tox1_wifi_bt_install.sh"
ssh root@$HostIP "bash /root/tox1_wifi_bt_install.sh"
