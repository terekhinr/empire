@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Empire VPS: откат SSH config
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cursor_vps_tailscale_rollback_pc.ps1"
echo.
pause
