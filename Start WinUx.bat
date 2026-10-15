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

rem Wait up to 20 seconds for the panel. If it never comes up, show why.
for /l %%i in (1,1,20) do (
  powershell -NoProfile -Command "try { Invoke-WebRequest http://127.0.0.1:7777/ -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul && exit /b 0
  timeout /t 1 /nobreak >nul
)
echo.
echo  * WinUx didn't start.
if exist "winux-error.log" (
  echo  * Here's what went wrong ^(also saved in winux-error.log^):
  echo.
  type "winux-error.log"
) else (
  echo  * Trying again with error messages on...
  echo.
  "%PYW:pythonw=python%" server.py
)
echo.
pause
