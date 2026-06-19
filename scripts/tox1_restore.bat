@echo off
chcp 65001 >nul
echo.
echo === TOX1: диагностика + restore ===
echo Пароль root — один раз. Окно НЕ закрывать.
echo.
ssh -t root@192.168.1.41 "echo '=== supervisor ===' && ha supervisor info && echo && echo '=== backups ===' && ha backups list && echo && echo '=== RESTORE 204bd3e1 (10-15 min) ===' && ha backups restore 204bd3e1 && echo && echo '=== ГОТОВО ==='"
echo.
echo Если выше красное / Error — сфоткайте этот экран.
pause
