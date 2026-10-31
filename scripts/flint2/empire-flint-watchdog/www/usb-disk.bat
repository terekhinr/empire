@echo off
chcp 65001 >nul
setlocal
:: Один раз: Credential Manager + Z: + планировщик.
:: После отвала Samba Windows сама переподключит — бат больше не нужен.

set "SHARE=\\192.168.1.1\download"
set "EMPIRE_DIR=%LOCALAPPDATA%\Empire"
set "REMOUNT=%EMPIRE_DIR%\remount-flint.cmd"
set "TASK=EmpireFlintUSB"

if not exist "%EMPIRE_DIR%" mkdir "%EMPIRE_DIR%"

> "%REMOUNT%" (
  echo @echo off
  echo rem Empire: silent remount Flint USB share
  echo ping -n 1 -w 800 192.168.1.1 ^>nul 2^>^&1 ^|^| exit /b 0
  echo cmdkey /add:192.168.1.1 /user:home /pass:home ^>nul 2^>^&1
  echo if exist Z:\ ^(
  echo   dir Z:\ ^>nul 2^>^&1 ^&^& exit /b 0
  echo ^)
  echo net use Z: /delete /y ^>nul 2^>^&1
  echo net use Z: %SHARE% /user:home home /persistent:yes ^>nul 2^>^&1
  echo exit /b 0
)

echo Сохраняю home/home в Windows (Credential Manager^)...
cmdkey /add:192.168.1.1 /user:home /pass:home >nul 2>&1

echo Подключаю Z: -^> %SHARE%
net use Z: /delete /y >nul 2>&1
net use Z: %SHARE% /user:home home /persistent:yes
if errorlevel 1 (
  echo.
  echo FAILED. Выключи Amnezia/VPN на этом ПК, открой \\192.168.1.1\download, потом снова этот файл.
  pause
  exit /b 1
)

echo Ставлю автопереподключение (вход в Windows + каждые 5 мин^)...
schtasks /Delete /TN "%TASK%" /F >nul 2>&1
schtasks /Create /TN "%TASK%" /TR "\"%REMOUNT%\"" /SC MINUTE /MO 5 /RU "%USERNAME%" /F >nul 2>&1
if errorlevel 1 (
  schtasks /Create /TN "%TASK%" /TR "cmd /c \"%REMOUNT%\"" /SC MINUTE /MO 5 /RU "%USERNAME%" /F >nul 2>&1
)
schtasks /Create /TN "%TASK%-logon" /TR "\"%REMOUNT%\"" /SC ONLOGON /RU "%USERNAME%" /F >nul 2>&1
if errorlevel 1 (
  schtasks /Create /TN "%TASK%-logon" /TR "cmd /c \"%REMOUNT%\"" /SC ONLOGON /RU "%USERNAME%" /F >nul 2>&1
)

echo.
echo Готово. Z: подключён. Бат больше не запускай — Windows сама вернёт диск после отвала.
echo Снять авто: schtasks /Delete /TN %TASK% /F ^& schtasks /Delete /TN %TASK%-logon /F
explorer Z:
endlocal
