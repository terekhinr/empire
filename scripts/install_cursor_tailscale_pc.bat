@echo off
REM Двойной клик из F:\Media Empire — настройка Tailscale SSH для Cursor
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cursor_vps_tailscale_setup_pc.ps1" -InstallTailscale
pause
