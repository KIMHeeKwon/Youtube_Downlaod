@echo off
REM Start the local web UI and open the browser.
cd /d "%~dp0.."
set "PATH=%cd%\tools;%USERPROFILE%\.local\bin;%USERPROFILE%\.deno\bin;%PATH%"
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000"
echo Starting YouTube downloader web UI... (close this window to stop)
uv run uvicorn webapp:app --port 8000
