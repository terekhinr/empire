@echo off
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cursor_vps_tailscale_rollback_pc.ps1"
pause
