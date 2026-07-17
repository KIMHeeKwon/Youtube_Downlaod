@echo off
REM YouTube downloader one-click installer (double-click me)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] Install failed. See messages above.
) else (
  echo.
  echo [OK] Install finished. Use the "YouTube Downloader" desktop shortcut.
)
pause
