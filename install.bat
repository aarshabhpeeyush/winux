@echo off
rem Double-click this to install WinUx. It asks before installing anything.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause
