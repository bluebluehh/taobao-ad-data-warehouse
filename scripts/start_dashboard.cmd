@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Starting the Taobao ad dashboard...
echo Open http://127.0.0.1:8765 in your browser after the service starts.
echo Keep this window open. Press Ctrl+C to stop the service.
powershell.exe -NoProfile -Command "python -u -m warehouse.serve --self-check 2>&1 | Tee-Object -FilePath 'output/midterm/dashboard_startup.log'"
echo.
echo Service stopped. If port 8765 is already in use, an existing dashboard may be running.
pause
