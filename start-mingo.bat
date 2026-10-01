@echo off
chcp 65001 >nul
title Mingo（このウィンドウを閉じると終了します）
cd /d "%~dp0backend"
start /b "" .venv\Scripts\python.exe -m uvicorn main:app
cd /d "%~dp0frontend"
start /b "" npm run dev -- --strictPort
timeout /t 4 /nobreak >nul
start "" http://localhost:5173
echo.
echo Mingo 起動中。終わるときはこのウィンドウを閉じてください。
pause >nul
