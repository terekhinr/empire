@echo off
REM С ПК в LAN. Логин telnet: admin / пароль от веб Keenetic
echo === Keenetic heal ===
echo 1) telnet 192.168.1.1
echo 2) exec sh
echo 3) export PATH=/opt/bin:/opt/sbin:$PATH
echo 4) curl -fsSL http://193.233.232.48:8787/55-minimal-nfqws2.sh ^| sh
echo.
echo Или одной строкой SSH Entware (пароль root: keenetic):
ssh -o StrictHostKeyChecking=no -p 222 root@192.168.1.1 "curl -fsSL http://193.233.232.48:8787/55-minimal-nfqws2.sh | sh"
pause
