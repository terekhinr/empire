@echo off
REM Nightly rclone voice backup (replaces Empire-Voice-Sync every 15 min).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_voice_rclone_nightly_windows.ps1"
if errorlevel 1 (echo FAILED & pause & exit /b 1)
echo OK. Task Empire-Voice-Rclone-Nightly created for 03:00.
timeout /t 5
