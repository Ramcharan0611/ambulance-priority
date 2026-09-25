@echo off
title Smart Ambulance Corridor System
echo =====================================================================
echo  Starting Smart Ambulance Traffic Signal Priority System...
echo =====================================================================
cd /d "%~dp0"
echo Server launching on http://127.0.0.1:8000
start "" "http://127.0.0.1:8000"
python -m uvicorn app:app_asgi --host 127.0.0.1 --port 8000
pause
