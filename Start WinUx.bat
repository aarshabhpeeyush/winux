@echo off
rem Starts WinUx quietly in the background and opens the control panel.
rem (If WinUx is already running from startup, this just opens the panel.)
cd /d "%~dp0"
set "PYW="
if exist ".pythonw" set /p PYW=<".pythonw"
if not defined PYW (
  where pyw >nul 2>nul && set "PYW=pyw"
)
if not defined PYW (
  echo WinUx can't find Python. Run install.bat first.
  pause
  exit /b 1
)
start "" "%PYW%" server.py
