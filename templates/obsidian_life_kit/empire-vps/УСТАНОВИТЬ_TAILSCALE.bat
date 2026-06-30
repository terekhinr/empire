@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo Empire VPS: Tailscale + SSH setup for Cursor
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cursor_vps_tailscale_setup_pc.ps1" -InstallTailscale
set ERR=%ERRORLEVEL%
echo.
if %ERR% NEQ 0 (
  echo ERROR: script failed with code %ERR%
) else (
  echo SUCCESS: you can connect in Cursor via empire-vps-ts
)
pause
exit /b %ERR%
