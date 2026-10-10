@echo off
chcp 65001 >nul
title Hisoblash Bot & Mini App Server
echo ===================================================
echo 💰 Запуск Hisoblash Finance Bot & Web App...
echo ===================================================
cd /d "%~dp0"
.\.venv\Scripts\python.exe -m app
if %errorlevel% neq 0 (
    echo.
    echo ⚠️ Бот завершил работу с кодом ошибки: %errorlevel%
    pause
)
