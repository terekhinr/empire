@echo off
chcp 65001 >nul
echo Connecting Z: to \\192.168.1.1\download
net use Z: /delete /y >nul 2>&1
net use Z: \\192.168.1.1\download /user:home home /persistent:yes
if errorlevel 1 (
  echo FAILED. Turn off Amnezia/VPN, then run this file again.
  pause
  exit /b 1
)
explorer Z:
